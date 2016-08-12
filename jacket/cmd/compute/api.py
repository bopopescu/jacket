# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for Nova API.

Starts both the EC2 and OpenStack APIs in separate greenthreads.

"""

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
import six

from jacket.compute import config
from jacket.compute import exception
from jacket.i18n import _LE, _LW
from jacket.objects import compute
from jacket.compute import service
from jacket.compute import utils
from jacket import version

CONF = cfg.CONF
CONF.import_opt('enabled_apis', 'compute.service')
CONF.import_opt('enabled_ssl_apis', 'compute.service')


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, "compute")
    utils.monkey_patch()
    compute.register_all()
    log = logging.getLogger(__name__)

    gmr.TextGuruMeditation.setup_autorun(version)

    launcher = service.process_launcher()
    started = 0
    for api in CONF.enabled_apis:
        should_use_ssl = api in CONF.enabled_ssl_apis
        try:
            server = service.WSGIService(api, use_ssl=should_use_ssl)
            launcher.launch_service(server, workers=server.workers or 1)
            started += 1
        except exception.PasteAppNotFound as ex:
            log.warning(
                _LW("%s. ``enabled_apis`` includes bad values. "
                    "Fix to remove this warning."), six.text_type(ex))

    if started == 0:
        log.error(_LE('No APIs were started. '
                      'Check the enabled_apis config option.'))
        sys.exit(1)

    launcher.wait()
