# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""Starter script for Nova Network."""

import sys
import traceback

from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from jacket.compute.conductor import rpcapi as conductor_rpcapi
import jacket.compute.conf
from jacket.compute import config
import jacket.db.compute.api
from jacket.compute import exception
from jacket.i18n import _LE, _LW
from jacket.objects import compute
from jacket.objects.compute import base as objects_base
from jacket.compute import service
from jacket.compute import utils
from jacket import version

CONF = jacket.compute.conf.CONF
CONF.import_opt('network_topic', 'compute.network.rpcapi')
LOG = logging.getLogger('compute.network')


def block_db_access():
    class NoDB(object):
        def __getattr__(self, attr):
            return self

        def __call__(self, *args, **kwargs):
            stacktrace = "".join(traceback.format_stack())
            LOG.error(_LE('No db access allowed in compute-network: %s'),
                      stacktrace)
            raise exception.DBNotAllowed('compute-network')

    jacket.db.compute.api.IMPL = NoDB()


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, "compute")
    utils.monkey_patch()
    compute.register_all()

    gmr.TextGuruMeditation.setup_autorun(version)

    if not CONF.conductor.use_local:
        block_db_access()
        objects_base.NovaObject.indirection_api = \
            conductor_rpcapi.ConductorAPI()
    else:
        LOG.warning(_LW('Conductor local mode is deprecated and will '
                        'be removed in a subsequent release'))

    server = service.Service.create(binary='compute-network',
                                    topic=CONF.network_topic,
                                    db_allowed=CONF.conductor.use_local)
    service.serve(server)
    service.wait()
