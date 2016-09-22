#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from eventlet import greenthread
import collections
import time

from novaclient import client as nc
from novaclient import exceptions
from oslo_log import log as logging
from retrying import retry
import six

from jacket import conf
from jacket.drivers.fs import exception_ex
from jacket.drivers.fs.clients import client_plugin
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LI
from jacket.i18n import _LW


LOG = logging.getLogger(__name__)

CONF = conf.CONF
CLIENT_RETRY_LIMIT = CONF.fs_clients.client_retry_limit
REBOOT_SOFT, REBOOT_HARD = 'SOFT', 'HARD'


class NovaClientPlugin(client_plugin.ClientPlugin):
    CLIENT_NAME = 'fs_nova'
    DEFAULT_API_VERSION = "2"
    DEFAULT_REGION_NAME = "RegionOne"
    DEFAULT_CATALOG_INFO = {
        "2": {"service_type": "compute",
              "service_name": "nova",
              "interface": "publicURL"},
    }

    SUPPORTED_VERSION = ["2"]

    deferred_server_statuses = ['BUILD',
                                'HARD_REBOOT',
                                'PASSWORD',
                                'REBOOT',
                                'RESCUE',
                                'RESIZE',
                                'REVERT_RESIZE',
                                'SHUTOFF',
                                'SUSPENDED',
                                'VERIFY_RESIZE']

    exceptions_module = exceptions

    def _create(self, version=None):
        version = self.fs_context.version

        extensions = nc.discover_extensions(version)

        kwargs = self.fs_context.to_dict()
        kwargs.update(
            {
                'extensions': extensions,
                'http_log_debug': self._get_client_option(self.CLIENT_NAME,
                                                          'http_log_debug')
            }
        )
        kwargs.pop('version')

        kwargs['api_key'] = kwargs.pop("password")

        client = nc.Client(version, **kwargs)
        return client

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.OverLimit)

    def is_bad_request(self, ex):
        return isinstance(ex, exceptions.BadRequest)

    def is_conflict(self, ex):
        return isinstance(ex, exceptions.Conflict)

    def is_unprocessable_entity(self, ex):
        http_status = (getattr(ex, 'http_status', None) or
                       getattr(ex, 'code', None))
        return (isinstance(ex, exceptions.ClientException) and
                http_status == 422)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_connection_err)
    def get_server(self, server):
        """Return fresh server object.

        Substitutes Nova's NotFound for Heat's EntityNotFound,
        to be returned to user as HTTP error.
        """
        try:
            return self.client().servers.get(server)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Server', name=server)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_connection_err)
    def get_server_by_name(self, server_name):
        """Return fresh server object.

        Substitutes Nova's NotFound for Heat's EntityNotFound,
        to be returned to user as HTTP error.
        """
        server_list = self.client().servers.list(
            search_opts={'name': server_name})

        if server_list and len(server_list) > 0:
            server = server_list[0]
        else:
            server = None

        return server

    def fetch_server(self, server_id):
        """Fetch fresh server object from Nova.

        Log warnings and return None for non-critical API errors.
        Use this method in various ``check_*_complete`` resource methods,
        where intermittent errors can be tolerated.
        """
        server = None
        try:
            server = self.client().servers.get(server_id)
        except exceptions.OverLimit as exc:
            LOG.warning(_LW("Received an OverLimit response when "
                            "fetching server (%(id)s) : %(exception)s"),
                        {'id': server_id,
                         'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warning(_LW("Received the following exception when "
                            "fetching server (%(id)s) : %(exception)s"),
                            {'id': server_id,
                             'exception': exc})
            else:
                raise
        return server

    def list(self, detailed=True, search_opts=None, marker=None, limit=None,
             sort_keys=None, sort_dirs=None):
        return self.client().servers.list(detailed=detailed,
                                          search_opts=search_opts,
                                          marker=marker,
                                          limit=limit,
                                          sort_keys=sort_keys,
                                          sort_dirs=sort_dirs)

    def refresh_server(self, server):
        """Refresh server's attributes.

        Also log warnings for non-critical API errors.
        """
        try:
            server.get()
        except exceptions.OverLimit as exc:
            LOG.warning(_LW("Server %(name)s (%(id)s) received an OverLimit "
                            "response during server.get(): %(exception)s"),
                        {'name': server.name,
                         'id': server.id,
                         'exception': exc})
        except exceptions.ClientException as exc:
            if ((getattr(exc, 'http_status', getattr(exc, 'code', None)) in
                 (500, 503))):
                LOG.warning(_LW('Server "%(name)s" (%(id)s) received the '
                                'following exception during server.get(): '
                                '%(exception)s'),
                            {'name': server.name,
                             'id': server.id,
                             'exception': exc})
            else:
                raise

    def get_status(self, server):
        """Return the server's status.

        :param server: server object
        :returns: status as a string
        """
        # Some clouds append extra (STATUS) strings to the status, strip it
        return server.status.split('(')[0]

    def _check_active(self, server, res_name='Server'):
        """Check server status.

        Accepts both server IDs and server objects.
        Returns True if server is ACTIVE,
        raises errors when server has an ERROR or unknown to Heat status,
        returns False otherwise.

        :param res_name: name of the resource to use in the exception message

        """
        # not checking with is_uuid_like as most tests use strings e.g. '1234'
        if isinstance(server, six.string_types):
            server = self.fetch_server(server)
            if server is None:
                return False
            else:
                status = self.get_status(server)
        else:
            status = self.get_status(server)
            if status != 'ACTIVE':
                self.refresh_server(server)
                status = self.get_status(server)

        if status in self.deferred_server_statuses:
            return False
        elif status == 'ACTIVE':
            return True
        elif status == 'ERROR':
            fault = getattr(server, 'fault', {})
            raise exception.ResourceInError(
                resource_status=status,
                status_reason=_("Message: %(message)s, Code: %(code)s") % {
                    'message': fault.get('message', _('Unknown')),
                    'code': fault.get('code', _('Unknown'))
                })
        else:
            raise exception.ResourceUnknownStatus(
                resource_status=server.status,
                result=_('%s is not active') % res_name)

    def find_flavor_by_name_or_id(self, flavor):
        """Find the specified flavor by name or id.

        :param flavor: the name of the flavor to find
        :returns: the id of :flavor:
        """
        return self._find_flavor_id(self.fs_context.tenant_id,
                                    flavor)

    def _find_flavor_id(self, tenant_id, flavor):
        # tenant id in the signature is used for the memoization key,
        # that would differentiate similar resource names across tenants.
        return self.get_flavor(flavor).id

    def get_flavor(self, flavor_identifier):
        """Get the flavor object for the specified flavor name or id.

        :param flavor_identifier: the name or id of the flavor to find
        :returns: a flavor object with name or id :flavor:
        """
        try:
            flavor = self.client().flavors.get(flavor_identifier)
        except exceptions.NotFound:
            flavor = self.client().flavors.find(name=flavor_identifier)

        return flavor

    def get_host(self, host_name):
        """Get the host id specified by name.

        :param host_name: the name of host to find
        :returns: the list of match hosts
        :raises: exception.EntityNotFound
        """

        host_list = self.client().hosts.list()
        for host in host_list:
            if host.host_name == host_name and host.service == self.COMPUTE:
                return host

        raise exception.EntityNotFound(entity='Host', name=host_name)

    @retry(stop_max_attempt_number=60,
           wait_fixed=1000,
           retry_on_result=client_plugin.retry_if_result_is_false)
    def check_delete_server_complete(self, server_id):
        """Wait for server to disappear from Nova."""
        try:
            server = self.fetch_server(server_id)
        except Exception as exc:
            self.ignore_not_found(exc)
            return True
        if not server:
            return False
        task_state_in_nova = getattr(server, 'OS-EXT-STS:task_state', None)
        # the status of server won't change until the delete task has done
        if task_state_in_nova == 'deleting':
            return False

        status = self.get_status(server)
        if status in ("DELETED", "SOFT_DELETED"):
            return True
        if status == 'ERROR':
            fault = getattr(server, 'fault', {})
            message = fault.get('message', 'Unknown')
            code = fault.get('code')
            errmsg = _("Server %(name)s delete failed: (%(code)s) "
                       "%(message)s") % dict(name=server.name,
                                             code=code,
                                             message=message)
            raise exception.ResourceInError(resource_status=status,
                                            status_reason=errmsg)
        return False

    def rename(self, server, name):
        """Update the name for a server."""
        server.update(name)

    def resize(self, server_id, flavor_id):
        """Resize the server."""
        server = self.fetch_server(server_id)
        if server:
            server.resize(flavor_id)
            return True
        else:
            return False

    def check_resize(self, server_id, flavor):
        """Verify that a resizing server is properly resized.

        If that's the case, confirm the resize, if not raise an error.
        """
        server = self.fetch_server(server_id)
        # resize operation is asynchronous so the server resize may not start
        # when checking server status (the server may stay ACTIVE instead
        # of RESIZE).
        if not server or server.status in ('RESIZE', 'ACTIVE'):
            return False
        if server.status == 'VERIFY_RESIZE':
            return True
        else:
            raise exception.Error(
                _("Resizing to '%(flavor)s' failed, status '%(status)s'") %
                dict(flavor=flavor, status=server.status))

    def verify_resize(self, server_id):
        server = self.fetch_server(server_id)
        if not server:
            return False
        status = self.get_status(server)
        if status == 'VERIFY_RESIZE':
            server.confirm_resize()
            return True
        else:
            msg = _("Could not confirm resize of server %s") % server_id
            raise exception.ResourceUnknownStatus(
                result=msg, resource_status=status)

    def check_verify_resize(self, server_id):
        server = self.fetch_server(server_id)
        if not server:
            return False
        status = self.get_status(server)
        if status == 'ACTIVE':
            return True
        if status == 'VERIFY_RESIZE':
            return False
        else:
            msg = _("Confirm resize for server %s failed") % server_id
            raise exception.ResourceUnknownStatus(
                result=msg, resource_status=status)

    def rebuild(self, server_id, image_id, password=None,
                preserve_ephemeral=False):
        """Rebuild the server and call check_rebuild to verify."""
        server = self.fetch_server(server_id)
        if server:
            server.rebuild(image_id, password=password,
                           preserve_ephemeral=preserve_ephemeral)
            return True
        else:
            return False

    def check_rebuild(self, server_id):
        """Verify that a rebuilding server is rebuilt.

        Raise error if it ends up in an ERROR state.
        """
        server = self.fetch_server(server_id)
        if server is None or server.status == 'REBUILD':
            return False
        if server.status == 'ERROR':
            raise exception.Error(
                _("Rebuilding server failed, status '%s'") % server.status)
        else:
            return True

    def server_to_ipaddress(self, server):
        """Return the server's IP address, fetching it from Nova."""
        try:
            server = self.client().servers.get(server)
        except exceptions.NotFound as ex:
            LOG.warning(_LW('Instance (%(server)s) not found: %(ex)s'),
                        {'server': server, 'ex': ex})
        else:
            for n in sorted(server.networks, reverse=True):
                if len(server.networks[n]) > 0:
                    return server.networks[n][0]

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_connection_err)
    def absolute_limits(self):
        """Return the absolute limits as a dictionary."""
        limits = self.client().limits.get()
        return dict([(limit.name, limit.value)
                    for limit in list(limits.absolute)])

    def get_console_urls(self, server):
        """Return dict-like structure of server's console urls.

        The actual console url is lazily resolved on access.
        """

        class ConsoleUrls(collections.Mapping):
            def __init__(self, server):
                self.console_methods = {
                    'novnc': server.get_vnc_console,
                    'xvpvnc': server.get_vnc_console,
                    'spice-html5': server.get_spice_console,
                    'rdp-html5': server.get_rdp_console,
                    'serial': server.get_serial_console
                }

            def __getitem__(self, key):
                try:
                    url = self.console_methods[key](key)['console']['url']
                except exceptions.BadRequest as e:
                    unavailable = 'Unavailable console type'
                    if unavailable in e.message:
                        url = e.message
                    else:
                        raise
                return url

            def __len__(self):
                return len(self.console_methods)

            def __iter__(self):
                return (key for key in self.console_methods)

        return ConsoleUrls(server)

    def attach_volume(self, server_id, volume_id, device):
        try:
            va = self.client().volumes.create_server_volume(
                server_id=server_id,
                volume_id=volume_id,
                device=device)
        except Exception as ex:
            if self.is_client_exception(ex):
                raise exception.Error(_(
                    "Failed to attach volume %(vol)s to server %(srv)s "
                    "- %(err)s") % {'vol': volume_id,
                                    'srv': server_id,
                                    'err': ex})
            else:
                raise
        return va.id

    def detach_volume(self, server_id, attach_id):
        # detach the volume using volume_attachment
        try:
            self.client().volumes.delete_server_volume(server_id, attach_id)
        except Exception as ex:
            if not (self.is_not_found(ex)
                    or self.is_bad_request(ex)):
                raise exception.Error(
                    _("Could not detach attachment %(att)s "
                      "from server %(srv)s.") % {'srv': server_id,
                                                 'att': attach_id})

    def check_detach_volume_complete(self, server_id, attach_id):
        """Check that nova server lost attachment.

        This check is needed for immediate reattachment when updating:
        there might be some time between cinder marking volume as 'available'
        and nova removing attachment from its own objects, so we
        check that nova already knows that the volume is detached.
        """
        try:
            self.client().volumes.get_server_volume(server_id, attach_id)
        except Exception as ex:
            self.ignore_not_found(ex)
            LOG.info(_LI("Volume %(vol)s is detached from server %(srv)s"),
                     {'vol': attach_id, 'srv': server_id})
            return True
        else:
            LOG.debug("Server %(srv)s still has attachment %(att)s." % {
                'att': attach_id, 'srv': server_id})
            return False

    def interface_detach(self, server_id, port_id):
        server = self.fetch_server(server_id)
        if server:
            server.interface_detach(port_id)
            return True
        else:
            return False

    def interface_list(self, server):
        return self.client().servers.interface_list(server)

    def interface_attach(self, server_id, port_id=None, net_id=None, fip=None):
        server = self.fetch_server(server_id)
        if server:
            server.interface_attach(port_id, net_id, fip)
            return True
        else:
            return False

    @retry(stop_max_attempt_number=60,
           wait_fixed=500,
           retry_on_result=client_plugin.retry_if_result_is_false)
    def check_interface_detach(self, server_id, port_id):
        server = self.fetch_server(server_id)
        if server:
            interfaces = server.interface_list()
            for iface in interfaces:
                if iface.port_id == port_id:
                    return False
        return True

    @retry(stop_max_attempt_number=60,
           wait_fixed=500,
           retry_on_result=client_plugin.retry_if_result_is_false)
    def check_interface_attach(self, server_id, port_id):
        server = self.fetch_server(server_id)
        if server:
            interfaces = server.interface_list()
            for iface in interfaces:
                if iface.port_id == port_id:
                    return True
        return False

    def _list_extensions(self):
        extensions = self.client().list_extensions.show_all()
        return set(extension.alias for extension in extensions)

    def has_extension(self, alias):
        """Check if specific extension is present."""
        return alias in self._list_extensions()

    def stop(self, server):
        return self.client().servers.stop(server)

    def start(self, server):
        return self.client().servers.start(server)

    def reboot(self, server, reboot_type=REBOOT_SOFT):
        """
        Reboot a server.

        :param server: The :class:`Server` (or its ID) to share onto.
        :param reboot_type: either :data:`REBOOT_SOFT` for a software-level
                reboot, or `REBOOT_HARD` for a virtual power cycle hard reboot.
        """
        self.client().servers.reboot(server, reboot_type)

    def create_server(self, name, image, flavor, meta=None, files=None,
               reservation_id=None, min_count=None,
               max_count=None, security_groups=None, userdata=None,
               key_name=None, availability_zone=None,
               block_device_mapping=None, block_device_mapping_v2=None,
               nics=None, scheduler_hints=None,
               config_drive=None, disk_config=None, **kwargs):
        """
        Create (boot) a new server.

        :param name: Something to name the server.
        :param image: The :class:`Image` to boot with.
        :param flavor: The :class:`Flavor` to boot onto.
        :param meta: A dict of arbitrary key/value metadata to store for this
                     server. A maximum of five entries is allowed, and both
                     keys and values must be 255 characters or less.
        :param files: A dict of files to overrwrite on the server upon boot.
                      Keys are file names (i.e. ``/etc/passwd``) and values
                      are the file contents (either as a string or as a
                      file-like object). A maximum of five entries is allowed,
                      and each file must be 10k or less.
        :param userdata: user data to pass to be exposed by the metadata
                      server this can be a file type object as well or a
                      string.
        :param reservation_id: a UUID for the set of servers being requested.
        :param key_name: (optional extension) name of previously created
                      keypair to inject into the instance.
        :param availability_zone: Name of the availability zone for instance
                                  placement.
        :param block_device_mapping: (optional extension) A dict of block
                      device mappings for this server.
        :param block_device_mapping_v2: (optional extension) A dict of block
                      device mappings for this server.
        :param nics:  (optional extension) an ordered list of nics to be
                      added to this server, with information about
                      connected networks, fixed ips, port etc.
        :param scheduler_hints: (optional extension) arbitrary key-value pairs
                            specified by the client to help boot an instance
        :param config_drive: (optional extension) value for config drive
                            either boolean, or volume-id
        :param disk_config: (optional extension) control how the disk is
                            partitioned when the server is created.  possible
                            values are 'AUTO' or 'MANUAL'.
        """
        return self.client().servers.create(name, image, flavor, meta, files,
               reservation_id, min_count,
               max_count, security_groups, userdata,
               key_name, availability_zone,
               block_device_mapping, block_device_mapping_v2,
               nics, scheduler_hints,
               config_drive, disk_config)

    def wait_for_server_in_specified_status(self, server, status):

        start = time.time()
        retries = self._get_client_option(self.CLIENT_NAME, "wait_retries")
        wait_retries_interval = self._get_client_option(
            self.CLIENT_NAME, "wait_retries_interval")
        if retries < 0:
            LOG.warning(_LW("Treating negative config value (%(retries)s) for "
                            "'block_device_retries' as 0."),
                        {'retries': retries})
        # (1) treat  negative config value as 0
        # (2) the configured value is 0, one attempt should be made
        # (3) the configured value is > 0, then the total number attempts
        #      is (retries + 1)
        attempts = 1
        if retries >= 1:
            attempts = retries + 1
        for attempt in range(1, attempts + 1):
            server = self.get_server(server)
            status_of_server = server.status
            if status_of_server == status:
                LOG.info(_LI("fs compute wait status(%(status)s) "
                             "successfully."),
                         status=status)
                return

            if status_of_server == "ERROR":
                raise exception_ex.ServerStatusException(
                    status=status_of_server)

            greenthread.sleep(wait_retries_interval)

        raise exception_ex.ServerStatusTimeoutException(server_id=server.id,
                                                        status=status_of_server,
                                                        timeout=int(
                                                            time.time() - start))

    def delete(self, server):
        """

        :param server: type Server
        :return:
        """
        return self.client().servers.delete(server)
