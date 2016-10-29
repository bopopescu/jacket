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

"""The images api."""

import webob
from oslo_log import log as logging
from webob import exc

from jacket import worker
from jacket.api.openstack import wsgi
from jacket.i18n import _LE, _LI

LOG = logging.getLogger(__name__)


class ImageMapperController(wsgi.Controller):
    """The images API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.config_api = worker.API()
        super(ImageMapperController, self).__init__()

    def show(self, req, id):
        """Return data about the given volume."""
        context = req.environ['jacket.context']

        try:
            image = self.config_api.image_mapper_get(context, id)
        except Exception as ex:
            LOG.error(_LE("get image(%(image_id)s) mapper failed, ex = %(ex)s"), image_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'image_mapper': image}

    def delete(self, req, id):
        """Delete a image mapper."""
        context = req.environ['jacket.context']

        LOG.info(_LI("Delete image mapper with id: %s"), id)

        try:
            image = self.config_api.image_mapper_get(context, id)
            self.config_api.image_mapper_delete(context, id)
        except Exception as ex:
            LOG.error(_LE("delete image mapper with id: %(id)s failed, ex = %(ex)s"), id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return webob.Response(status_int=202)

    def detail(self, req):
        """Returns a detailed list of images mapper."""
        context = req.environ['jacket.context']

        try:
            images = self.config_api.image_mapper_all(context)
        except Exception as ex:
            LOG.error(_LE("get images mapper failed, ex = %(ex)s"), ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'images_mapper': images}

    def create(self, req, body):
        """Creates a new image mapper."""
        context = req.environ['jacket.context']

        if not self.is_valid_body(body, 'image_mapper'):
            raise exc.HTTPUnprocessableEntity()

        image_mapper = body['image_mapper']
        if 'image_id' not in image_mapper:
            raise exc.HTTPUnprocessableEntity()

        if 'provider_image_id' not in image_mapper:
            raise exc.HTTPUnprocessableEntity()

        image_id = image_mapper.pop('image_id')
        project_id = image_mapper.pop('project_id', None)

        try:
            image = self.config_api.image_mapper_create(context, image_id,
                                                        project_id, image_mapper)
        except Exception as ex:
            LOG.error(_LE("create image(%(image_id)s) mapper failed, ex = %(ex)s"),
                      image_id=image_id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'image_mapper': image}

    def update(self, req, id, body):
        """Update a image mapper."""
        context = req.environ['jacket.context']
        if not self.is_valid_body(body, 'image_mapper'):
            raise exc.HTTPUnprocessableEntity()

        image_mapper = body['image_mapper']
        project_id = image_mapper.pop('project_id', None)
        try:
            image = self.config_api.image_mapper_update(context, id, project_id,
                                                        image_mapper)
        except Exception as ex:
            LOG.exception(_LE("update image(%(image_id)s) mapper failed, "
                          "ex = %(ex)s"), image_id=id, ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'image_mapper': image}

def create_resource(ext_mgr):
    return wsgi.Resource(ImageMapperController(ext_mgr))
