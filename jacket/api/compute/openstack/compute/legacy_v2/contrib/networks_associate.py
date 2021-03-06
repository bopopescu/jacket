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

import webob
from webob import exc

from jacket.api.compute.openstack import extensions
from jacket.api.compute.openstack import wsgi
from jacket import context as nova_context
from jacket.compute import exception
from jacket.i18n import _
from jacket.compute import network

authorize = extensions.extension_authorizer('compute', 'networks_associate')


class NetworkAssociateActionController(wsgi.Controller):
    """Network Association API Controller."""

    def __init__(self, network_api=None):
        self.network_api = network_api or network.API()

    @wsgi.action("disassociate_host")
    def _disassociate_host_only(self, req, id, body):
        context = req.environ['compute.context']
        authorize(context)
        # NOTE(shaohe-feng): back-compatible with db layer hard-code
        # admin permission checks.  call db API objects.Network.associate
        nova_context.require_admin_context(context)

        try:
            self.network_api.associate(context, id, host=None)
        except exception.NetworkNotFound:
            msg = _("Network not found")
            raise exc.HTTPNotFound(explanation=msg)
        except NotImplementedError:
            msg = _('Disassociate host is not implemented by the configured '
                    'Network API')
            raise exc.HTTPNotImplemented(explanation=msg)
        return webob.Response(status_int=202)

    @wsgi.action("disassociate_project")
    def _disassociate_project_only(self, req, id, body):
        context = req.environ['compute.context']
        authorize(context)
        # NOTE(shaohe-feng): back-compatible with db layer hard-code
        # admin permission checks.  call db API objects.Network.associate
        nova_context.require_admin_context(context)

        try:
            self.network_api.associate(context, id, project=None)
        except exception.NetworkNotFound:
            msg = _("Network not found")
            raise exc.HTTPNotFound(explanation=msg)
        except NotImplementedError:
            msg = _('Disassociate project is not implemented by the '
                    'configured Network API')
            raise exc.HTTPNotImplemented(explanation=msg)

        return webob.Response(status_int=202)

    @wsgi.action("associate_host")
    def _associate_host(self, req, id, body):
        context = req.environ['compute.context']
        authorize(context)
        # NOTE(shaohe-feng): back-compatible with db layer hard-code
        # admin permission checks.  call db API objects.Network.associate
        nova_context.require_admin_context(context)

        try:
            self.network_api.associate(context, id,
                                       host=body['associate_host'])
        except exception.NetworkNotFound:
            msg = _("Network not found")
            raise exc.HTTPNotFound(explanation=msg)
        except NotImplementedError:
            msg = _('Associate host is not implemented by the configured '
                    'Network API')
            raise exc.HTTPNotImplemented(explanation=msg)

        return webob.Response(status_int=202)


class Networks_associate(extensions.ExtensionDescriptor):
    """Network association support."""

    name = "NetworkAssociationSupport"
    alias = "os-networks-associate"
    namespace = ("http://docs.openstack.org/compute/ext/"
                 "networks_associate/api/v2")
    updated = "2012-11-19T00:00:00Z"

    def get_controller_extensions(self):
        extension = extensions.ControllerExtension(
                self, 'os-networks', NetworkAssociateActionController())

        return [extension]
