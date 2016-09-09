# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
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

"""
Handles all requests relating to volumes + cinder.
"""

import collections
import copy
import functools
import sys
import time

from novaclient import client as nova_client
from novaclient import exceptions as nova_exception
from novaclient import service_catalog
from keystoneauth1 import exceptions as keystone_exception
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
import six

from jacket import conf
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LE
from jacket.i18n import _LW


CONF = conf.CONF
CINDER_OPT_GROUP = 'fs_nova'

LOG = logging.getLogger(__name__)
DEFAULT_REGION_NAME = "RegionOne"
DEFAULT_CATALOG_INFO = {
                        "2": {"service_type": "compute",
                              "service_name": "nova",
                              "endpoint_type": "publicURL"},
                        }


def fs_novaclient(context, version=None, username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None, endpoint_type=None,
                 region_name=None, *args, **kwargs):

    if version is None:
        version = CONF.fs_nova.default_version

    if version not in DEFAULT_CATALOG_INFO.keys():
        raise exception.FsNovaVersionNotSupport(version=version)

    if not username or not password or not project_id or not auth_url:
        raise exception.FsNovaNotUserOrPass()

    if not service_type:
        service_type = DEFAULT_CATALOG_INFO[version]["service_type"]

    if not service_name:
        service_name = DEFAULT_CATALOG_INFO[version]["service_name"]

    if not endpoint_type:
        endpoint_type = DEFAULT_CATALOG_INFO[version]["endpoint_type"]

    if not region_name:
        region_name = DEFAULT_REGION_NAME

    return nova_client.Client(version, username=username, api_key=password,
                                project_id=project_id, auth_url=auth_url,
                                service_type=service_type, service_name=service_name,
                                endpoint_type=endpoint_type, region_name=region_name,
                                *args, **kwargs)


class FsNovaClientWrapper(object):
    """fs cinder client wrapper class that implements retries."""

    def __init__(self, context=None, is_static=True, version=None,
                 username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None,
                 endpoint_type=None, region_name=None,
                 *args, **kwargs):

        self.context = context
        self.version = version
        self.username = username
        self.password = password
        self.project_id = project_id
        self.auth_url = auth_url
        self.service_type = service_type
        self.service_name = service_name
        self.endpoint_type = endpoint_type
        self.region_name = region_name
        self.args = args
        self.kwargs = kwargs
        if is_static:
            self.client = self._create_fs_nova_client()
        else:
            self.client = None

        if CONF.fs_nova.num_retries < 0:
            LOG.warning(_LW(
                "num_retries shouldn't be a negative value. "
                "The number of retries will be set to 0 until this is"
                "corrected in the jacket.conf."))
            CONF.set_override('num_retries', 0, 'fs_nova')

    def _create_fs_nova_client(self):
        """Create a client that we'll use for every call."""
        return fs_novaclient(self.context, self.version, self.username,
                                self.password, self.project_id, self.auth_url,
                                self.service_type, self.service_name,
                                self.endpoint_type, self.region_name,
                                *(self.args), **(self.kwargs))

    def call(self, context, method, *args, **kwargs):
        """Call a glance client method.

        If we get a connection error,
        retry the request according to CONF.glance_num_retries.
        """
        version = self.version

        retry_excs = (nova_exception.ClientException)
        num_attempts = 1 + CONF.fs_nova.num_retries

        for attempt in range(1, num_attempts + 1):
            client = self.client or self._create_fs_nova_client(context,
                                                                version)
            try:
                controller = getattr(client,
                                     kwargs.pop('controller', 'servers'))
                return getattr(controller, method)(*args, **kwargs)
            except retry_excs as e:
                extra = "retrying"
                error_msg = _LE("Error contacting cinder server "
                                " for '%(method)s', "
                                "%(extra)s.")
                if attempt == num_attempts:
                    extra = 'done trying'
                    LOG.exception(error_msg, {'method': method,
                                              'extra': extra})
                    raise exception.FsNovaConnectFailed()

                LOG.exception(error_msg, {'method': method,
                                          'extra': extra})
                time.sleep(1)


class FsNovaService(object):
    """API for interacting with the volume manager."""

    def __init__(self, context=None, is_static=True, version=None,
                 username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None,
                 endpoint_type=None, region_name=None,
                 *args, **kwargs):
        self.client = FsNovaClientWrapper(context, is_static, version,
                                            username, password, project_id,
                                            auth_url, service_type, service_name,
                                            endpoint_type, region_name, *args, **kwargs)


