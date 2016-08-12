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

import ast

from oslo_log import log as logging
from oslo_utils import uuidutils
import webob
from webob import exc

from jacket.api.openstack import wsgi
from jacket.i18n import _LI


LOG = logging.getLogger(__name__)


class ImagesmapperController(wsgi.Controller):
    """The images API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.jacket_api = jacket.API()
        super(ImagesmapperController, self).__init__()

    def show(self, req, id):
        """Return data about the given volume."""
        context = req.environ['jacket.context']

        # Not found exception will be handled at the wsgi level
        image = self.jacket_api.get(context, id)
        # todo return

    def delete(self, req, id):
        """Delete a volume."""
        context = req.environ['jacket.context']

        LOG.info(_LI("Delete image with id: %s"), id)

        # Not found exception will be handled at the wsgi level
        image = self.jacket_api.get(context, id)
        self.volume_api.delete(context, image)
        return webob.Response(status_int=202)

    def index(self, req):
        """Returns a summary list of volumes."""
        # todo
        pass

    def detail(self, req):
        """Returns a detailed list of volumes."""
        # todo
        pass

    def create(self, req, body):
        """Creates a new volume."""
        # todo
        pass

    def update(self, req, id, body):
        """Update a volume."""
        context = req.environ['jacket.context']
        # todo
        pass


def create_resource(ext_mgr):
    return wsgi.Resource(ImagesmapperController(ext_mgr))
