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
import time
import traceback

from cinderclient import client as cc
from cinderclient import exceptions
from oslo_log import log as logging

from jacket import conf
from jacket.drivers.fs import exception_ex
from jacket.drivers.fs.clients import client_plugin
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LI
from jacket.i18n import _LW


LOG = logging.getLogger(__name__)

CONF = conf.CONF


class CinderClientPlugin(client_plugin.ClientPlugin):

    exceptions_module = exceptions
    CLIENT_NAME = 'fs_cinder'
    SUPPORTED_VERSION = [V2, V3] = ['2', '3']
    DEFAULT_API_VERSION = V2
    DEFAULT_CATALOG_INFO = {
        V2: {"service_type": "volumev2",
          "service_name": "cinderv2",
          "interface": "publicURL"},
        V3: {"service_type": "volumev3",
              "service_name": "cinderv3",
              "interface": "publicURL"},
    }

    def _create(self, version=None):
        version = self.fs_context.version
        extensions = cc.discover_extensions(version)

        args = self.fs_context.to_dict()
        args.update(
            {
                'extensions': extensions,
                'http_log_debug': self._get_client_option(self.CLIENT_NAME,
                                                          'http_log_debug')
            }
        )

        args.pop('version')
        args['api_key'] = args.pop("password")

        client = cc.Client(version, **args)
        return client

    def _list_extensions(self):
        extensions = self.client().list_extensions.show_all()
        return set(extension.alias for extension in extensions)

    def has_extension(self, alias):
        """Check if specific extension is present."""
        return alias in self._list_extensions()

    def get_volume(self, volume):
        try:
            return self.client().volumes.get(volume)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Volume', name=volume)

    def get_volume_by_name(self, volume_name):
        volume_list = self.client().volumes.list(
            search_opts={'name': volume_name})
        if volume_list and len(volume_list) > 0:
            return volume_list[0]
        else:
            return None

    def get_volume_snapshot(self, snapshot):
        try:
            return self.client().volume_snapshots.get(snapshot)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='VolumeSnapshot',
                                           name=snapshot)

    def get_volume_backup(self, backup):
        try:
            return self.client().backups.get(backup)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Volume backup',
                                           name=backup)

    def get_volume_type(self, volume_type):
        vt_id = None
        volume_type_list = self.client().volume_types.list()
        for vt in volume_type_list:
            if volume_type in [vt.name, vt.id]:
                vt_id = vt.id
                break
        if vt_id is None:
            raise exception.EntityNotFound(entity='VolumeType',
                                           name=volume_type)

        return vt_id

    def get_volume_type_by_id(self, volume_type_id):
        volume_type = self.client().volume_types.get(volume_type_id)
        return volume_type

    def get_qos_specs(self, qos_specs):
        try:
            qos = self.client().qos_specs.get(qos_specs)
        except exceptions.NotFound:
            qos = self.client().qos_specs.find(name=qos_specs)
        return qos.id

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.OverLimit)

    def is_conflict(self, ex):
        return (isinstance(ex, exceptions.ClientException) and
                ex.code == 409)

    def check_detach_volume_complete(self, vol_id):
        try:
            vol = self.client().volumes.get(vol_id)
        except Exception as ex:
            self.ignore_not_found(ex)
            return True

        if vol.status in ('in-use', 'detaching'):
            LOG.debug('%s - volume still in use' % vol_id)
            return False

        LOG.debug('Volume %(id)s - status: %(status)s' % {
            'id': vol.id, 'status': vol.status})

        if vol.status not in ('available', 'deleting'):
            LOG.debug("Detachment failed - volume %(vol)s "
                      "is in %(status)s status" % {"vol": vol.id,
                                                   "status": vol.status})
            raise exception.ResourceUnknownStatus(
                resource_status=vol.status,
                result=_('Volume detachment failed'))
        else:
            return True

    def check_attach_volume_complete(self, vol_id):
        vol = self.client().volumes.get(vol_id)
        if vol.status in ('available', 'attaching'):
            LOG.debug("Volume %(id)s is being attached - "
                      "volume status: %(status)s" % {'id': vol_id,
                                                     'status': vol.status})
            return False

        if vol.status != 'in-use':
            LOG.debug("Attachment failed - volume %(vol)s is "
                      "in %(status)s status" % {"vol": vol_id,
                                                "status": vol.status})
            raise exception.ResourceUnknownStatus(
                resource_status=vol.status,
                result=_('Volume attachment failed'))

        LOG.info(_LI('Attaching volume %(id)s complete'), {'id': vol_id})
        return True

    def wait_for_volume_in_specified_status(self, vol_id, status):

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
            LOG.debug("+++hw, attempt = %d", attempt)
            volume = self.client().volumes.get(vol_id)
            status_of_volume = volume.status
            if volume.status == status:
                LOG.info(_LI("fs volume wait status(%(status)s) successfully."),
                         status=status)
                return

            if volume.status == 'ERROR' or volume.status == 'error':
                raise exception_ex.VolumeCreateException(volume_id=volume.id)

            greenthread.sleep(wait_retries_interval)

        raise exception_ex.VolumeStatusTimeoutException(volume_id=volume.id,
                                                        status=status_of_volume,
                                                        timeout=int(time.time() - start))

    def volume_create(self, size=None, snapshot_id=None, source_volid=None,
                      display_name=None, display_description=None,
                      volume_type=None, user_id=None,
                      project_id=None, availability_zone=None,
                      metadata=None, imageRef=None, shareable=False):
        return self.client().volumes.create(
            size, snapshot_id=snapshot_id,
            source_volid=source_volid, name=display_name,
            description=display_description,
            volume_type=volume_type, user_id=user_id,
            project_id=project_id, availability_zone=availability_zone,
            metadata=metadata, imageRef=imageRef)

    def volume_delete(self, volume):
        """Delete a volume.

        :param volume: The :class:`Volume` to delete.
        """
        return self.client().volumes.delete(volume)

    def wait_for_volume_deleted(self, volume, timeout):
        start = int(time.time())
        while True:
            time.sleep(2)
            try:
                volume = self.client().volumes.get(volume.id)
                status_of_volume = volume.status
                cost_time = int(time.time()) - start
                LOG.debug('volume: %s status is: %s, cost time: %s' % (
                volume.id, status_of_volume, str(cost_time)))
            except Exception as e:
                LOG.debug('volume: %s is deleted' % volume.id)
                LOG.debug('exception: %s' % traceback.format_exc(e))
                break
            if int(time.time()) - start >= timeout:
                raise exception_ex.VolumeDeleteTimeoutException(volume_id=volume.id)
