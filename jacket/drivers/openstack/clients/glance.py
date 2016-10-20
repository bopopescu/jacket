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

import functools
import logging as py_logging

from glanceclient import client as gc
from glanceclient import exc
from glanceclient.openstack.common.apiclient import exceptions

from oslo_log import log as logging
from oslo_utils import excutils
from retrying import retry
import six
import six.moves.urllib.parse as urlparse

from keystoneauth1 import discover
from keystoneauth1 import exceptions as ks_exc
from keystoneauth1.identity import v2 as v2_auth
from keystoneauth1.identity import v3 as v3_auth
from keystoneauth1 import loading

from jacket import conf
from jacket.drivers.openstack import exception_ex
from jacket import exception
from jacket.i18n import _, _LW
from jacket.drivers.openstack.clients import client_plugin
from argparse import Namespace

CONF = conf.CONF
CLIENT_RETRY_LIMIT = CONF.clients_drivers.client_retry_limit

LOG = logging.getLogger(__name__)


def wrap_auth_failed(function):
    @functools.wraps(function)
    def decorated_function(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except (exceptions.Unauthorized):
            with excutils.save_and_reraise_exception():
                self.os_context.auth_refresh()
                self.invalidate()
                raise exception_ex.Unauthorized()

    return decorated_function


class GlanceClientPlugin(client_plugin.ClientPlugin):
    exceptions_module = [exceptions, exc]
    CLIENT_NAME = 'glance'

    SUPPORTED_VERSION = [V1, V2] = ['1', '2']
    DEFAULT_API_VERSION = V2
    DEFAULT_CATALOG_INFO = {
        V1: {"service_type": "image",
             "service_name": "glance",
             "interface": "publicURL"},
        V2: {"service_type": "image",
             "service_name": "glance",
             "interface": "publicURL"},
    }

    def __init__(self, os_context):

        # make sure keystoneauth1 no debug log, otherwise download maybe slow
        py_logging.getLogger('keystoneauth1').setLevel(py_logging.WARNING)
        super(GlanceClientPlugin, self).__init__(os_context)

    def _create(self, version=None):
        version = self.os_context.version

        args = self.os_context.to_dict()
        args.update(
            {
                'http_log_debug': self._get_client_option(self.CLIENT_NAME,
                                                          'http_log_debug')
            }
        )
        args.pop('version')

        namespace = Namespace()

        key_values = {'ca_file': 'os_cacert', 'cert_file': 'os_cert',
                      'key_file': 'os_key', 'insecure': 'insecure'}

        for key, value in key_values.iteritems():
            setattr(namespace, value,
                    args.pop(key, self._get_client_option(self.CLIENT_NAME,
                                                          key)))

        setattr(namespace, 'timeout', None)

        ks_session = loading.load_session_from_argparse_arguments(
            namespace)
        auth_plugin_kwargs = self._get_kwargs_to_create_auth_plugin(**args)

        ks_session.auth = self._get_keystone_auth_plugin(
            ks_session=ks_session, **auth_plugin_kwargs)
        kwargs = {'session': ks_session}

        endpoint_type = args['interface'] or 'public'
        service_type = args['service_type'] or 'image'
        endpoint = ks_session.get_endpoint(
            service_type=service_type,
            interface=endpoint_type,
            region_name=args['region_name'])

        client = gc.Client(version, endpoint, **kwargs)
        return client

    def _get_kwargs_to_create_auth_plugin(self, **kwargs):
        ret_kwargs = {
            'auth_url': kwargs.get('auth_url'),
            'username': kwargs.get("username"),
            'user_id': kwargs.get("user_id"),
            'user_domain_id': kwargs.get("user_domain_id"),
            'user_domain_name': kwargs.get("user_domain_name"),
            'password': kwargs.get("password"),
            'tenant_name': kwargs.get("tenant_name"),
            'tenant_id': kwargs.get("tenant_id"),
            'project_name': kwargs.get("project_id"),
            # 'project_id': kwargs.get("project_id"),
            'project_domain_name': kwargs.get("project_domain_name"),
            'project_domain_id': kwargs.get("project_domain_id"),
        }
        return ret_kwargs

    def _get_keystone_auth_plugin(self, ks_session, **kwargs):
        # discover the supported keystone versions using the given auth url
        auth_url = kwargs.pop('auth_url', None)
        (v2_auth_url, v3_auth_url) = self._discover_auth_versions(
            session=ks_session,
            auth_url=auth_url)

        # Determine which authentication plugin to use. First inspect the
        # auth_url to see the supported version. If both v3 and v2 are
        # supported, then use the highest version if possible.
        user_id = kwargs.pop('user_id', None)
        username = kwargs.pop('username', None)
        password = kwargs.pop('password', None)
        user_domain_name = kwargs.pop('user_domain_name', None)
        user_domain_id = kwargs.pop('user_domain_id', None)
        # project and tenant can be used interchangeably
        project_id = (kwargs.pop('project_id', None) or
                      kwargs.pop('tenant_id', None))
        project_name = (kwargs.pop('project_name', None) or
                        kwargs.pop('tenant_name', None))
        project_domain_id = kwargs.pop('project_domain_id', None)
        project_domain_name = kwargs.pop('project_domain_name', None)
        auth = None

        use_domain = (user_domain_id or
                      user_domain_name or
                      project_domain_id or
                      project_domain_name)
        use_v3 = v3_auth_url and (use_domain or (not v2_auth_url))
        use_v2 = v2_auth_url and not use_domain

        if use_v3:
            auth = v3_auth.Password(
                v3_auth_url,
                user_id=user_id,
                username=username,
                password=password,
                user_domain_id=user_domain_id,
                user_domain_name=user_domain_name,
                project_id=project_id,
                project_name=project_name,
                project_domain_id=project_domain_id,
                project_domain_name=project_domain_name)
        elif use_v2:
            auth = v2_auth.Password(
                v2_auth_url,
                username,
                password,
                tenant_id=project_id,
                tenant_name=project_name)
        else:
            # if we get here it means domain information is provided
            # (caller meant to use Keystone V3) but the auth url is
            # actually Keystone V2. Obviously we can't authenticate a V3
            # user using V2.
            exc.CommandError("Credential and auth_url mismatch. The given "
                             "auth_url is using Keystone V2 endpoint, which "
                             "may not able to handle Keystone V3 credentials. "
                             "Please provide a correct Keystone V3 auth_url.")

        return auth

    def _discover_auth_versions(self, session, auth_url):
        # discover the API versions the server is supporting base on the
        # given URL
        v2_auth_url = None
        v3_auth_url = None
        try:
            ks_discover = discover.Discover(session=session, url=auth_url)
            v2_auth_url = ks_discover.url_for('2.0')
            v3_auth_url = ks_discover.url_for('3.0')
        except ks_exc.ClientException as e:
            # Identity service may not support discover API version.
            # Lets trying to figure out the API version from the original URL.
            url_parts = urlparse.urlparse(auth_url)
            (scheme, netloc, path, params, query, fragment) = url_parts

            path = path.lower()
            if '/v3' in path:
                v3_auth_url = auth_url
            elif '/v2' in path:
                v2_auth_url = auth_url
            else:
                # not enough information to determine the auth version
                msg = ('Unable to determine the Keystone version '
                       'to authenticate with using the given '
                       'auth_url. Identity service may not support API '
                       'version discovery. Please provide a versioned '
                       'auth_url instead. error=%s') % (e)
                raise exc.CommandError(msg)

        return (v2_auth_url, v3_auth_url)

    def _find_with_attr(self, entity, **kwargs):
        """Find a item for entity with attributes matching ``**kwargs``."""
        matches = list(self._findall_with_attr(entity, **kwargs))
        num_matches = len(matches)
        if num_matches == 0:
            msg = _("No %(name)s matching %(args)s.") % {
                'name': entity,
                'args': kwargs
            }
            raise exception_ex.NotFound(msg)
        elif num_matches > 1:
            msg = _("No %(name)s unique match found for %(args)s.") % {
                'name': entity,
                'args': kwargs
            }
            raise exception_ex.NoUniqueMatch(msg)
        else:
            return matches[0]

    def _findall_with_attr(self, entity, **kwargs):
        """Find all items for entity with attributes matching ``**kwargs``."""
        func = getattr(self.client(), entity)
        filters = {'filters': kwargs}
        return func.list(**filters)

    def is_not_found(self, ex):
        return isinstance(ex, (exceptions.NotFound, exc.HTTPNotFound))

    def is_over_limit(self, ex):
        return isinstance(ex, exc.HTTPOverLimit)

    def is_conflict(self, ex):
        return isinstance(ex, (exceptions.Conflict, exc.Conflict))

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def find_image_by_name_or_id(self, image_identifier):
        """Return the ID for the specified image name or identifier.

        :param image_identifier: image name or a UUID-like identifier
        :returns: the id of the requested :image_identifier:
        """
        return self._find_image_id(image_identifier)

    def _find_image_id(self, image_identifier):
        # tenant id in the signature is used for the memoization key,
        # that would differentiate similar resource names across tenants.
        return self.get_image(image_identifier).id

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_image(self, image_identifier):
        """Return the image object for the specified image name/id.

        :param image_identifier: image name
        :returns: an image object with name/id :image_identifier:
        """
        try:
            return self.client().images.get(image_identifier)
        except exc.HTTPNotFound:
            return self._find_with_attr('images', name=image_identifier)

    @retry(stop_max_attempt_number=1800,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_image_active_complete(self, image_id):
        try:
            image_ref = self.get_image(image_id)
        except Exception:
            raise
        if not image_ref:
            return False

        LOG.debug("-------------image_ref = %s, type = %s", image_ref,
                  type(image_ref))

        status = image_ref.status
        LOG.debug("+++hw, wait image(%s), current status = %s", image_id,
                  status)

        if status == "active":
            return True

        if status == 'ERROR':
            errmsg = _("image(%s) wait failed") % image_id
            raise exception.ResourceInError(resource_status=status,
                                            status_reason=errmsg)

        return False

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def delete(self, image_id):
        try:
            self.client().images.delete(image_id)
        except exc.HTTPNotFound:
            LOG.warn(_LW("image(%s) is not exist"), image_id)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def data(self, image_id):
        image_data = self.client().images.data(image_id)
        return DataFile(image_data)


class DataFile(object):
    """An iterator wrapper with image.

    :note: Use only with iterator that yield strings.
    """

    def __init__(self, wrapped):
        self._wrapped = wrapped

    def __iter__(self):
        return self

    def next(self):
        try:
            data = six.next(self._wrapped)
            return data
        except StopIteration:
            raise

    def read(self, length):
        return self.next()

    def __len__(self):
        return len(self._wrapped)

    # In Python 3, __next__() has replaced next().
    __next__ = next
