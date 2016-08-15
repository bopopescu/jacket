#   Copyright 2011 OpenStack Foundation
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

"""The rescue mode extension."""

from oslo_config import cfg
from oslo_utils import uuidutils
from webob import exc

from jacket.api.compute.openstack import common
from jacket.api.compute.openstack.compute.schemas import rescue
from jacket.api.compute.openstack import extensions
from jacket.api.compute.openstack import wsgi
from jacket.api.compute import validation
from jacket.compute import cloud
from jacket.compute import exception
from jacket.i18n import _
from jacket.compute import utils


ALIAS = "os-rescue"
CONF = cfg.CONF
CONF.import_opt('enable_instance_password',
                'cloud.api.openstack.cloud.legacy_v2.servers')

authorize = extensions.os_compute_authorizer(ALIAS)


class RescueController(wsgi.Controller):
    def __init__(self, *args, **kwargs):
        super(RescueController, self).__init__(*args, **kwargs)
        self.compute_api = cloud.API(skip_policy_check=True)

    def _rescue_image_validation(self, image_ref):
        image_uuid = image_ref.split('/').pop()

        if not uuidutils.is_uuid_like(image_uuid):
            msg = _("Invalid rescue_image_ref provided.")
            raise exc.HTTPBadRequest(explanation=msg)

        return image_uuid

    # TODO(cyeoh): Should be responding here with 202 Accept
    # because rescue is an async call, but keep to 200
    # for backwards compatibility reasons.
    @extensions.expected_errors((400, 404, 409, 501))
    @wsgi.action('rescue')
    @validation.schema(rescue.rescue)
    def _rescue(self, req, id, body):
        """Rescue an instance."""
        context = req.environ["cloud.context"]
        authorize(context)

        if body['rescue'] and 'adminPass' in body['rescue']:
            password = body['rescue']['adminPass']
        else:
            password = utils.generate_password()

        instance = common.get_instance(self.compute_api, context, id)
        rescue_image_ref = None
        if body['rescue'] and 'rescue_image_ref' in body['rescue']:
            rescue_image_ref = self._rescue_image_validation(
                body['rescue']['rescue_image_ref'])

        try:
            self.compute_api.rescue(context, instance,
                                    rescue_password=password,
                                    rescue_image_ref=rescue_image_ref)
        except exception.InstanceUnknownCell as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except exception.InstanceIsLocked as e:
            raise exc.HTTPConflict(explanation=e.format_message())
        except exception.InstanceInvalidState as state_error:
            common.raise_http_conflict_for_instance_invalid_state(state_error,
                                                                  'rescue', id)
        except exception.InvalidVolume as volume_error:
            raise exc.HTTPConflict(explanation=volume_error.format_message())
        except exception.InstanceNotRescuable as non_rescuable:
            raise exc.HTTPBadRequest(
                explanation=non_rescuable.format_message())

        if CONF.enable_instance_password:
            return {'adminPass': password}
        else:
            return {}

    @wsgi.response(202)
    @extensions.expected_errors((404, 409, 501))
    @wsgi.action('unrescue')
    def _unrescue(self, req, id, body):
        """Unrescue an instance."""
        context = req.environ["cloud.context"]
        authorize(context)
        instance = common.get_instance(self.compute_api, context, id)
        try:
            self.compute_api.unrescue(context, instance)
        except exception.InstanceUnknownCell as e:
            raise exc.HTTPNotFound(explanation=e.format_message())
        except exception.InstanceIsLocked as e:
            raise exc.HTTPConflict(explanation=e.format_message())
        except exception.InstanceInvalidState as state_error:
            common.raise_http_conflict_for_instance_invalid_state(state_error,
                                                                  'unrescue',
                                                                  id)


class Rescue(extensions.V21APIExtensionBase):
    """Instance rescue mode."""

    name = "Rescue"
    alias = ALIAS
    version = 1

    def get_resources(self):
        return []

    def get_controller_extensions(self):
        controller = RescueController()
        extension = extensions.ControllerExtension(self, 'servers', controller)
        return [extension]
