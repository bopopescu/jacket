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

import ast

from oslo_log import log as logging
import webob
from webob import exc

from jacket.api.cloud_config.openstack import wsgi
from jacket.i18n import _LE, _LI
from jacket import cloud_config

LOG = logging.getLogger(__name__)


class ProjectMapperController(wsgi.Controller):
    """The projects API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.config_api = cloud_config.API()
        super(ProjectMapperController, self).__init__()

    def show(self, req, project_id):
        """Return data about the given volume."""
        context = req.environ['jacket.context']

        try:
            project = self.config_api.project_mapper_get(context, project_id)
        except Exception as ex:
            LOG.error(_LE("get project(%(project_id)s) mapper failed, ex = %(ex)s"), project_id=project_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'project_mapper': project}

    def delete(self, req, project_id):
        """Delete a project mapper."""
        context = req.environ['jacket.context']

        LOG.info(_LI("Delete project mapper with id: %s"), project_id)

        try:
            project = self.config_api.project_mapper_get(context, project_id)
            self.config_api.project_mapper_delete(context, project_id)
        except Exception as ex:
            LOG.error(_LE("delete project mapper with id: %(id)s failed, ex = %(ex)s"), id=project_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return webob.Response(status_int=202)

    def detail(self, req):
        """Returns a detailed list of projects mapper."""
        context = req.environ['jacket.context']

        try:
            projects = self.config_api.project_mapper_all(context)
        except Exception as ex:
            LOG.error(_LE("get projects mapper failed, ex = %(ex)s"), ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'projects_mapper': projects}

    def create(self, req, body):
        """Creates a new project mapper."""
        context = req.environ['jacket.context']

        if not self.is_valid_body(body, 'project_mapper'):
            raise exc.HTTPUnprocessableEntity()

        project_mapper = body['project_mapper']
        if 'project_id' not in project_mapper:
            raise exc.HTTPUnprocessableEntity()

        project_id = project_mapper.pop('project_id')

        try:
            project = self.config_api.project_mapper_create(context, project_id, project_mapper)
        except Exception as ex:
            LOG.error(_LE("create project(%(project_id)s) mapper failed, ex = %(ex)s"),
                      project_id=project_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'project_mapper': project}

    def update(self, req, project_id, body):
        """Update a project mapper."""
        context = req.environ['jacket.context']
        if not self.is_valid_body(body, 'project_mapper'):
            raise exc.HTTPUnprocessableEntity()

        project_mapper = body['project_mapper']
        try:
            project = self.config_api.project_mapper_update(context, project_id, project_mapper)
        except Exception as ex:
            LOG.error(_LE("update project(%(project_id)s) mapper failed, ex = %(ex)s"),
                      project_id=project_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'project_mapper': project}

def create_resource(ext_mgr):
    return wsgi.Resource(ProjectMapperController(ext_mgr))
