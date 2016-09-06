# Copyright 2011 Justin Santa Barbara
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

"""The project mapper api."""

import webob
from oslo_log import log as logging
from webob import exc

from jacket import worker
from jacket.api.openstack import wsgi
from jacket.i18n import _LE, _LI

LOG = logging.getLogger(__name__)


class ProjectMapperController(wsgi.Controller):
    """The projects API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.config_api = worker.API()
        super(ProjectMapperController, self).__init__()

    def show(self, req, project_id):
        pass

    def delete(self, req, project_id):
        pass

    def detail(self, req):
        pass

    def create(self, req, body):
        pass

    def update(self, req, project_id, body):
        pass

def create_resource(ext_mgr):
    return wsgi.Resource(ProjectMapperController(ext_mgr))
