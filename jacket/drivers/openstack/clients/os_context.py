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

import copy

from oslo_log import log as logging

from jacket import exception
from jacket.drivers.openstack import exception_ex
from jacket.db.extend import api as db_api
from jacket.i18n import _LE


LOG = logging.getLogger(__name__)


class OsClientContext(object):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """

    def __init__(self, context, version=None, service_type=None,
                 service_name=None, interface=None, **kwargs):

        self.init_os_context(context)
        self.context = context
        self.version = version
        self.service_type = service_type
        self.service_name = service_name
        self.interface = interface
        self.insecure = kwargs.pop('insecure', None)
        self.cacert = kwargs.pop('cacert', None)
        self.timeout = kwargs.pop('timeout', None)
        self.kwargs = kwargs

    def to_dict(self):
        values = {}
        values.update({
            'version': getattr(self, 'version', None),
            'username': getattr(self, 'username', None),
            'password': getattr(self, 'password', None),
            'project_id': getattr(self, 'project_id', None),
            'auth_url': getattr(self, 'auth_url', None),
            'service_type': getattr(self, 'service_type', None),
            'interface': getattr(self, 'interface', None),
            'region_name': getattr(self, 'region_name', None),
            'insecure': getattr(self, 'insecure', None),
            'cacert': getattr(self, 'cacert', None),
            'timeout': getattr(self, 'timeout', None),
        })

        if self.kwargs:
            for k, v in self.kwargs.iteritems():
                values.update({k: v})
        return values

    def elevated(self, read_deleted=None):
        """Return a version of this context with admin flag set."""
        context = copy.copy(self)

        return context

    def __str__(self):
        return "<OsContext %s>" % self.to_dict()

    def init_os_context(self, context):
        project_info = db_api.project_mapper_get(context, context.project_id)
        if not project_info:
            project_info = db_api.project_mapper_get(context,
                                                     "default")

        if not project_info:
            raise exception_ex.AccountNotConfig()

        LOG.debug("+++hw, project_info = %s", project_info)

        self.username = project_info.pop('user', None)
        self.password = project_info.pop("pwd", None)
        self.project_id = project_info.pop("tenant", None)
        self.auth_url = project_info.pop("auth_url", None)
        self.region_name = project_info.pop("region", None)

        if not self.username or not self.password or not self.project_id or \
            not self.auth_url:
            raise exception_ex.AccountNotConfig()

        #self.kwargs = project_info

    def auth_needs_refresh(self):
        return False
