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

import abc
import weakref

from keystoneauth1 import exceptions
from keystoneauth1.identity import generic
from keystoneauth1 import plugin
from oslo_config import cfg
from oslo_log import log as logging

import requests
import six

from jacket import conf
from jacket import exception as jacket_exception
from jacket.drivers.openstack import exception_ex

CONF = conf.CONF
LOG = logging.getLogger(__name__)


def get_client_option(client, option):
    # look for the option in the [clients_${client}] section
    # unknown options raise cfg.NoSuchOptError
    try:
        group_name = 'clients_' + client
        return getattr(getattr(CONF, group_name), option)
    except (cfg.NoSuchGroupError, cfg.NoSuchOptError):
        pass  # do not error if the client is unknown
    # look for the option in the generic [clients] section

    return getattr(CONF.clients_drivers, option)


@six.add_metaclass(abc.ABCMeta)
class ClientPlugin(object):
    # Module which contains all exceptions classes which the client
    # may emit
    exceptions_module = None

    CLIENT_NAME = ''

    # supported service types, service like cinder support multiple service
    # types, so its used in list format
    DEFAULT_CATALOG_INFO = {}

    DEFAULT_API_VERSION = None

    SUPPORTED_VERSION = []

    def __init__(self, os_context):
        self._os_context = os_context
        self.invalidate()

    @property
    def os_context(self):
        ctxt = self._os_context
        assert ctxt is not None, "Need a reference to the context"
        return ctxt

    _get_client_option = staticmethod(get_client_option)

    def invalidate(self):
        """Invalidate/clear any cached client."""
        self._client_instances = {}

        if not self.os_context.version:
            self.os_context.version = self.DEFAULT_API_VERSION

        version = self.os_context.version

        if self.os_context.version not in self.DEFAULT_CATALOG_INFO.keys():
            raise jacket_exception.OsNovaVersionNotSupport(
                version=version)

        if not self.os_context.service_name:
            self.os_context.service_name = \
                self.DEFAULT_CATALOG_INFO[version]['service_name']

        if not self.os_context.service_type:
            self.os_context.service_type = \
                self.DEFAULT_CATALOG_INFO[version]['service_type']

        if not self.os_context.interface:
            self.os_context.interface = \
                self.DEFAULT_CATALOG_INFO[version]['interface']
        if not self.os_context.insecure:
            self.os_context.insecure = self._get_client_option(
                self.CLIENT_NAME, 'insecure')

        if not self.os_context.cacert:
            self.os_context.cacert = self._get_client_option(
                self.CLIENT_NAME, 'ca_file')
        if not self.os_context.timeout:
            self.os_context.timeout = self._get_client_option(
                self.CLIENT_NAME, 'timeout')

    def client(self, version=None):
        if not version:
            version = self.DEFAULT_API_VERSION

        if (version in self._client_instances
            and not self.os_context.auth_needs_refresh()):
            return self._client_instances[version]

        if version not in self.SUPPORTED_VERSION:
            raise jacket_exception.OsInvalidServiceVersion(
                version=version,
                service=self._get_service_name())

        self._client_instances[version] = self._create(version=version)

        return self._client_instances[version]

    @abc.abstractmethod
    def _create(self, version=None):
        """Return a newly created client."""
        pass

    def url_for(self, **kwargs):
        keystone_session = self.os_context.keystone_session

        def get_endpoint():
            return keystone_session.get_endpoint(**kwargs)

        # NOTE(jamielennox): use the session defined by the keystoneclient
        # options as traditionally the token was always retrieved from
        # keystoneclient.
        try:
            kwargs.setdefault('interface', kwargs.pop('endpoint_type'))
        except KeyError:
            pass

        reg = self.os_context.region_name or cfg.CONF.region_name_for_services
        kwargs.setdefault('region_name', reg)
        url = None
        try:
            url = get_endpoint()
        except exceptions.EmptyCatalog:
            endpoint = keystone_session.get_endpoint(
                None, interface=plugin.AUTH_INTERFACE)
            token = keystone_session.get_token(None)
            token_obj = generic.Token(endpoint, token)
            auth_ref = token_obj.get_access(keystone_session)
            if auth_ref.has_service_catalog():
                self.os_context.reload_auth_plugin()
                url = get_endpoint()

        # NOTE(jamielennox): raising exception maintains compatibility with
        # older keystoneclient service catalog searching.
        if url is None:
            raise exceptions.EndpointNotFound()

        return url

    def is_client_exception(self, ex):
        """Returns True if the current exception comes from the client."""
        if self.exceptions_module:
            if isinstance(self.exceptions_module, list):
                for m in self.exceptions_module:
                    if type(ex) in six.itervalues(m.__dict__):
                        return True
            else:
                return type(ex) in six.itervalues(
                    self.exceptions_module.__dict__)
        return False

    def is_not_found(self, ex):
        """Returns True if the exception is a not-found."""
        return False

    def is_over_limit(self, ex):
        """Returns True if the exception is an over-limit."""
        return False

    def is_conflict(self, ex):
        """Returns True if the exception is a conflict."""
        return False

    def ignore_not_found(self, ex):
        """Raises the exception unless it is a not-found."""
        return self.is_not_found(ex)

    def ignore_conflict_and_not_found(self, ex):
        """Raises the exception unless it is a conflict or not-found."""
        return self.is_conflict(ex) or self.is_not_found(ex)

    def does_endpoint_exist(self,
                            service_type,
                            service_name):
        endpoint_type = self._get_client_option(service_name,
                                                'endpoint_type')
        try:
            self.url_for(service_type=service_type,
                         endpoint_type=endpoint_type)
            return True
        except exceptions.EndpointNotFound:
            return False


def retry_if_ignore_exe(exception):
    return isinstance(exception, requests.ConnectionError) or \
           isinstance(exception, exception_ex.Unauthorized)


def retry_if_result_is_false(result):
    return result is False


def retry_auth_failed(exe):
    return isinstance(exe, exception_ex.Unauthorized)
