"""Starter script for Jacket Worker."""

import sys
import traceback

from oslo_concurrency import processutils
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr

from jacket.compute.conductor import rpcapi as conductor_rpcapi
import jacket.conf
from jacket.compute import config
import jacket.db.compute.api
from jacket.compute import exception
from jacket.i18n import _LE, _LW
from jacket import objects
from jacket.objects.compute import base as objects_base
from jacket import service
from jacket.compute import utils
from jacket import version

CONF = jacket.conf.CONF
CONF.import_opt('jacket_controller_topic', 'jacket.controller.rpcapi')
LOG = logging.getLogger('jacket.controller')


def block_db_access():
    class NoDB(object):
        def __getattr__(self, attr):
            return self

        def __call__(self, *args, **kwargs):
            stacktrace = "".join(traceback.format_stack())
            LOG.error(_LE('No db access allowed in jacket-controller: %s'),
                      stacktrace)
            raise exception.DBNotAllowed('jacket-controller')

    jacket.db.api.IMPL = NoDB()


def main():
    config.parse_args(sys.argv)
    logging.setup(CONF, 'jacket')
    utils.monkey_patch()
    objects.register_all()

    gmr.TextGuruMeditation.setup_autorun(version)

    # TODO(nkapotoxin) remove this config, db call is supposed to be local
    if not CONF.conductor.use_local:
        block_db_access()
        objects_base.NovaObject.indirection_api = \
            conductor_rpcapi.ConductorAPI()
    else:
        LOG.warning(_LW('Conductor local mode is deprecated and will '
                        'be removed in a subsequent release'))

    server = service.Service.create(binary='jacket-controller',
                                    topic=CONF.jacket_controller_topic,
                                    db_allowed=CONF.conductor.use_local)
    workers = CONF.jacket_controller_workers or processutils.get_worker_count()
    service.serve(server, workers)
    service.wait()
