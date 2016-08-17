#!/usr/bin/env python
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

"""Starter script for jacket OS API."""

import eventlet
eventlet.monkey_patch()

import logging as python_logging
import sys

from jacket import objects

from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

from jacket import i18n
i18n.enable_lazy()

# Need to register global_opts
from jacket.common import config
from jacket import base_rpc
from jacket import jacket_service
from jacket import utils
from jacket import version


CONF = cfg.CONF


def main():
    objects.register_all()
    gmr_opts.set_defaults(CONF)
    CONF(sys.argv[1:], project='jacket',
         version=version.version_string())
    config.set_middleware_defaults()
    logging.setup(CONF, "jacket")
    python_logging.captureWarnings(True)
    utils.monkey_patch()

    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)

    base_rpc.init(CONF)
    launcher = jacket_service.process_launcher()
    server = jacket_service.WSGIService('osapi_jacket')
    launcher.launch_service(server, workers=server.workers)
    launcher.wait()
