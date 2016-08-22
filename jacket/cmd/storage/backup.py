#!/usr/bin/env python

# Copyright (C) 2012 Hewlett-Packard Development Company, L.P.
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

"""Starter script for Cinder Volume Backup."""

import logging as python_logging
import sys

import eventlet
from oslo_config import cfg
from oslo_log import log as logging
from oslo_reports import guru_meditation_report as gmr
from oslo_reports import opts as gmr_opts

eventlet.monkey_patch()

from jacket.storage import i18n
i18n.enable_lazy()

# Need to register global_opts
from jacket.common.storage import config  # noqa
from jacket.objects import storage
from jacket import service
from jacket.storage import utils
from jacket.storage import version


CONF = cfg.CONF


def main():
    storage.register_all()
    gmr_opts.set_defaults(CONF)
    CONF(sys.argv[1:], project='storage',
         version=version.version_string())
    logging.setup(CONF, "storage")
    python_logging.captureWarnings(True)
    utils.monkey_patch()
    gmr.TextGuruMeditation.setup_autorun(version, conf=CONF)
    server = service.Service.create(binary='storage-backup')
    service.serve(server)
    service.wait()
