# Copyright 2011 OpenStack Foundation
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

from webob import exc

from jacket.compute import cloud
from jacket.api.compute.openstack import common
from jacket.api.compute.openstack.compute.views import addresses as views_addresses
from jacket.api.compute.openstack import extensions
from jacket.api.compute.openstack import wsgi
from jacket.i18n import _

ALIAS = 'ips'
authorize = extensions.os_compute_authorizer(ALIAS)


class IPsController(wsgi.Controller):
    """The servers addresses API controller for the OpenStack API."""
    # Note(gmann): here using V2 view builder instead of V3 to have V2.1
    # server ips response same as V2 which does not include "OS-EXT-IPS:type"
    # & "OS-EXT-IPS-MAC:mac_addr". If needed those can be added with
    # microversion by using V2.1 view builder.
    _view_builder_class = views_addresses.ViewBuilder

    def __init__(self, **kwargs):
        super(IPsController, self).__init__(**kwargs)
        self._compute_api = cloud.API(skip_policy_check=True)

    @extensions.expected_errors(404)
    def index(self, req, server_id):
        context = req.environ["compute.context"]
        authorize(context, action='index')
        instance = common.get_instance(self._compute_api, context, server_id)
        networks = common.get_networks_for_instance(context, instance)
        return self._view_builder.index(networks)

    @extensions.expected_errors(404)
    def show(self, req, server_id, id):
        context = req.environ["compute.context"]
        authorize(context, action='show')
        instance = common.get_instance(self._compute_api, context, server_id)
        networks = common.get_networks_for_instance(context, instance)
        if id not in networks:
            msg = _("Instance is not a member of specified network")
            raise exc.HTTPNotFound(explanation=msg)

        return self._view_builder.show(networks[id], id)


class IPs(extensions.V21APIExtensionBase):
    """Server addresses."""

    name = "Ips"
    alias = ALIAS
    version = 1

    def get_resources(self):
        parent = {'member_name': 'server',
                  'collection_name': 'servers'}
        resources = [
            extensions.ResourceExtension(
                ALIAS, IPsController(), parent=parent, member_name='ip')]

        return resources

    def get_controller_extensions(self):
        return []
