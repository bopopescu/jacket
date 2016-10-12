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

from jacket.api.extend import extensions
import jacket.api.openstack
from jacket.api.extend import versions
from jacket.api.extend.v1 import image_mapper
from jacket.api.extend.v1 import flavor_mapper
from jacket.api.extend.v1 import project_mapper
from jacket.api.extend.v1 import sub_flavor
from jacket.api.extend.v1 import sub_volume_type


class APIRouter(jacket.api.openstack.APIRouter):
    """Routes requests on the API to the appropriate controller and method."""
    ExtensionManager = extensions.ExtensionManager

    def _setup_routes(self, mapper, ext_mgr):
        self.resources['versions'] = versions.create_resource()
        mapper.connect("versions", "/",
                       controller=self.resources['versions'],
                       action='show',
                       conditions={"method": ['GET']})

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

        self.resources['sub_flavor'] = sub_flavor.create_resource(ext_mgr)
        mapper.connect("sub_flavor", '/{project_id}/sub_flavor/detail',
                       controller=self.resources['sub_flavor'],
                       action="detail",
                       conditions={"method": ['GET']})

        self.resources['sub_volume_type'] = \
            sub_volume_type.create_resource(ext_mgr)
        mapper.connect("sub_volume_type",
                       '/{project_id}/sub_volume_type/detail',
                       controller=self.resources['sub_volume_type'],
                       action="detail",
                       conditions={"method": ['GET']})
