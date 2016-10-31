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


class ImageSyncController(wsgi.Controller):
    """The flavors API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.worker_api = worker.API()
        super(ImageSyncController, self).__init__()

    def image_sync(self, req, body):
        context = req.environ['jacket.context']

        if not self.is_valid_body(body, 'image_sync'):
            raise exc.HTTPUnprocessableEntity()
        image_sync = body['image_sync']
        if 'image_id' not in image_sync:
            raise exc.HTTPUnprocessableEntity()
        return

def create_resource(ext_mgr):
    return wsgi.Resource(ImageSyncController(ext_mgr))
