# Copyright (c) 2012 OpenStack Foundation
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

"""VNC Console Proxy Server."""

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from jacket.compute import config
from jacket.objects import compute
from jacket.compute import service
from jacket import version

CONF = cfg.CONF

CONF.import_opt('consoleauth_topic', 'jacket.compute.consoleauth')


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, "compute")
    compute.register_all()

    gmr.TextGuruMeditation.setup_autorun(version)

    server = service.Service.create(binary='compute-consoleauth',
                                    topic=CONF.consoleauth_topic)
    service.serve(server)
    service.wait()
