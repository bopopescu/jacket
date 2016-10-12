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


class SubFlavorController(wsgi.Controller):
    """The flavors API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.worker_api = worker.API()
        super(SubFlavorController, self).__init__()

    def detail(self, req):
        """Returns a detailed list of flavors mapper."""
        context = req.environ['jacket.context']

        try:
            flavors = self.worker_api.sub_flavor_detail(context)
        except Exception as ex:
            LOG.exception(_LE("get sub flavors failed, ex = %(ex)s"),
                          ex=ex)
            raise exc.HTTPBadRequest(explanation=ex)
        return {'sub_flavors': flavors}

def create_resource(ext_mgr):
    return wsgi.Resource(SubFlavorController(ext_mgr))
