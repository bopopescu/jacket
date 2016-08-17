# Copyright 2011 OpenStack Foundation
# Copyright 2011 United States Government as represented by the
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
WSGI middleware for OpenStack jacket API.
"""

from jacket.api.jacket_api import extensions
import jacket.api.openstack
from jacket.api.jacket_api import versions
from jacket.api.jacket_api.v1 import image_mapper
from jacket.api.jacket_api.v1 import flavor_mapper
from jacket.api.jacket_api.v1 import project_mapper


class APIRouter(jacket.api.openstack.APIRouter):
    """Routes requests on the API to the appropriate controller and method."""
    ExtensionManager = extensions.ExtensionManager

    def _setup_routes(self, mapper, ext_mgr):
        self.resources['versions'] = versions.create_resource()
        mapper.connect("versions", "/",
                       controller=self.resources['versions'],
                       action='index')

        mapper.redirect("", "/")

        self.resources['image_mapper'] = image_mapper.create_resource(ext_mgr)
        mapper.resource("image_mapper", "image_mapper",
                        controller=self.resources['image_mapper'],
                        collection={'detail': 'GET'})

        self.resources['flavor_mapper'] = flavor_mapper.create_resource(ext_mgr)
        mapper.resource("flavor_mapper", "flavor_mapper",
                        controller=self.resources['flavor_mapper'],
                        collection={'detail': 'GET'})

        self.resources['project_mapper'] = project_mapper.create_resource(ext_mgr)
        mapper.resource("project_mapper", "project_mapper",
                        controller=self.resources['project_mapper'],
                        collection={'detail': 'GET'})
