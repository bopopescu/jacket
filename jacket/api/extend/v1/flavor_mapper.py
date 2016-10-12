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

"""The flavor mapper api."""

import webob
from oslo_log import log as logging
from webob import exc

from jacket import worker
from jacket.api.openstack import wsgi
from jacket.i18n import _LE, _LI

LOG = logging.getLogger(__name__)


class FlavorMapperController(wsgi.Controller):
    """The flavors API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.config_api = worker.API()
        super(FlavorMapperController, self).__init__()

    def show(self, req, id):
        """Return data about the given volume."""
        context = req.environ['jacket.context']

        try:
            flavor = self.config_api.flavor_mapper_get(context, id)
        except Exception as ex:
            LOG.error(
                _LE("get flavor(%(flavor_id)s) mapper failed, ex = %(ex)s"),
                flavor_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'flavor_mapper': flavor}

    def delete(self, req, id):
        """Delete a flavor mapper."""
        context = req.environ['jacket.context']

        LOG.info(_LI("Delete flavor mapper with id: %s"), id)

        try:
            flavor = self.config_api.flavor_mapper_get(context, id)
            self.config_api.flavor_mapper_delete(context, id)
        except Exception as ex:
            LOG.error(
                _LE("delete flavor mapper with id: %(id)s failed, ex = %(ex)s"),
                id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return webob.Response(status_int=202)

    def detail(self, req):
        """Returns a detailed list of flavors mapper."""
        context = req.environ['jacket.context']

        try:
            flavors = self.config_api.flavor_mapper_all(context)
        except Exception as ex:
            LOG.exception(_LE("get flavors mapper failed, ex = %(ex)s"), ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'flavors_mapper': flavors}

    def create(self, req, body):
        """Creates a new flavor mapper."""
        context = req.environ['jacket.context']

        if not self.is_valid_body(body, 'flavor_mapper'):
            raise exc.HTTPUnprocessableEntity()

        flavor_mapper = body['flavor_mapper']
        if 'flavor_id' not in flavor_mapper:
            raise exc.HTTPUnprocessableEntity()

        if 'dest_flavor_id' not in flavor_mapper:
            raise exc.HTTPUnprocessableEntity()

        flavor_id = flavor_mapper.pop('flavor_id')
        project_id = flavor_mapper.pop('project_id', None)

        try:
            flavor = self.config_api.flavor_mapper_create(context, flavor_id,
                                                          project_id,
                                                          flavor_mapper)
        except Exception as ex:
            LOG.exception(
                _LE("create flavor(%(flavor_id)s) mapper failed, ex = %(ex)s"),
                flavor_id=flavor_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'flavor_mapper': flavor}

    def update(self, req, id, body):
        """Update a flavor mapper."""
        context = req.environ['jacket.context']
        if not self.is_valid_body(body, 'flavor_mapper'):
            raise exc.HTTPUnprocessableEntity()

        flavor_mapper = body['flavor_mapper']
        project_id = flavor_mapper.pop('project_id', None)
        try:
            flavor = self.config_api.flavor_mapper_update(context, id,
                                                          project_id,
                                                          flavor_mapper)
        except Exception as ex:
            LOG.exception(
                _LE("update flavor(%(flavor_id)s) mapper failed, ex = %(ex)s"),
                flavor_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'flavor_mapper': flavor}


def create_resource(ext_mgr):
    return wsgi.Resource(FlavorMapperController(ext_mgr))
