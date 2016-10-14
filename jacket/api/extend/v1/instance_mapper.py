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

"""The instance mapper api."""

import webob
from oslo_log import log as logging
from webob import exc

from jacket import worker
from jacket.api.openstack import wsgi
from jacket.i18n import _LE, _LI

LOG = logging.getLogger(__name__)


class InstanceMapperController(wsgi.Controller):
    """The instance mappper API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.config_api = worker.API()
        super(InstanceMapperController, self).__init__()

    def show(self, req, id):
        """Return data about the given volume."""
        context = req.environ['jacket.context']

        try:
            instance = self.config_api.instance_mapper_get(context, id)
        except Exception as ex:
            LOG.error(
                _LE("get instance(%(instance_id)s) mapper failed, ex = %(ex)s"),
                instance_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'instance_mapper': instance}

    def delete(self, req, id):
        """Delete a instance mapper."""
        context = req.environ['jacket.context']

        LOG.info(_LI("Delete instance mapper with id: %s"), id)

        try:
            instance = self.config_api.instance_mapper_get(context, id)
            self.config_api.instance_mapper_delete(context, id)
        except Exception as ex:
            LOG.error(
                _LE(
                    "delete instance mapper with id: %(id)s failed, ex = %(ex)s"),
                id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return webob.Response(status_int=202)

    def detail(self, req):
        """Returns a detailed list of instances mapper."""
        context = req.environ['jacket.context']

        try:
            instances = self.config_api.instance_mapper_all(context)
        except Exception as ex:
            LOG.exception(_LE("get instances mapper failed, ex = %(ex)s"),
                          ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'instances_mapper': instances}

    def create(self, req, body):
        """Creates a new instance mapper."""
        context = req.environ['jacket.context']

        if not self.is_valid_body(body, 'instance_mapper'):
            raise exc.HTTPUnprocessableEntity()

        instance_mapper = body['instance_mapper']
        if 'instance_id' not in instance_mapper:
            raise exc.HTTPUnprocessableEntity()

        if 'dest_instance_id' not in instance_mapper:
            raise exc.HTTPUnprocessableEntity()

        instance_id = instance_mapper.pop('instance_id')
        project_id = instance_mapper.pop('project_id', None)

        try:
            instance = self.config_api.instance_mapper_create(context,
                                                              instance_id,
                                                              project_id,
                                                              instance_mapper)
        except Exception as ex:
            LOG.exception(
                _LE(
                    "create instance(%(instance_id)s) mapper failed, ex = %(ex)s"),
                instance_id=instance_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'instance_mapper': instance}

    def update(self, req, id, body):
        """Update a instance mapper."""
        context = req.environ['jacket.context']
        if not self.is_valid_body(body, 'instance_mapper'):
            raise exc.HTTPUnprocessableEntity()

        instance_mapper = body['instance_mapper']
        project_id = instance_mapper.pop('project_id', None)
        try:
            instance = self.config_api.instance_mapper_update(context, id,
                                                              project_id,
                                                              instance_mapper)
        except Exception as ex:
            LOG.exception(
                _LE(
                    "update instance(%(instance_id)s) mapper failed, ex = %(ex)s"),
                instance_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'instance_mapper': instance}


def create_resource(ext_mgr):
    return wsgi.Resource(InstanceMapperController(ext_mgr))
