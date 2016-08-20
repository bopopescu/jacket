
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

from jacket.api.jacket_api import common as jacket_api_common
from jacket.api.jacket_api.views import versions as jacket_api_views_versions
from jacket.api.middleware import sizelimit as jacket_api_sizelimit
from jacket.common import config as jacket_config
from jacket.db import base as jacket_db_base
from jacket.wsgi import common as wsgi_common
from jacket import jacket_service as jacket_base_service


def list_opts():
    return [
        ('DEFAULT',
            itertools.chain(
                jacket_api_common.api_common_opts,
                jacket_api_views_versions.versions_opts,
                [jacket_api_sizelimit.max_request_body_size_opt],
                jacket_config.core_opts,
                jacket_config.debug_opts,
                [jacket_db_base.db_driver_opt],
                wsgi_common.wsgi_opts,
                jacket_base_service.service_opts,
            )),
        ('wsgi',
         itertools.chain(
             wsgi_common.wsgi_opts,
         )),
    ]
