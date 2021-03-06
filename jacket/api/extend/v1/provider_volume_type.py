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

from oslo_log import log as logging
from webob import exc

from jacket.api.openstack import wsgi
from jacket import exception
from jacket.i18n import _LE
from jacket import worker

LOG = logging.getLogger(__name__)


class SubVolumeTypeController(wsgi.Controller):
    """The flavors API controller for the OpenStack API."""

    def __init__(self, ext_mgr):
        self.ext_mgr = ext_mgr
        self.worker_api = worker.API()
        super(SubVolumeTypeController, self).__init__()

    def detail(self, req):
        """Returns a detailed list of flavors mapper."""
        context = req.environ['jacket.context']

        try:
            volume_types = self.worker_api.sub_vol_type_detail(context)
        except exception.DriverNotSupported as ex:
            LOG.exception(_LE("get sub volume types failed, ex = %(ex)s"),
                          ex=ex.format_message())
            raise exc.HTTPBadRequest(explanation=ex.format_message())
        except Exception as ex:
            LOG.exception(_LE("get sub volume types failed, ex = %(ex)s"),
                          ex=ex.format_message())
            raise exc.HTTPBadRequest(explanation=ex.message)
        return {'sub_volume_types': volume_types}

def create_resource(ext_mgr):
    return wsgi.Resource(SubVolumeTypeController(ext_mgr))
