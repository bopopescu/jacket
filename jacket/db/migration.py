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

"""Database setup and migration commands."""

import threading

from oslo_config import cfg
from oslo_db import options
from stevedore import extension

INIT_VERSION = 000

_IMPL = None
_LOCK = threading.Lock()

options.set_defaults(cfg.CONF)

def get_backend(project=None):
    global _IMPL
    if _IMPL is None:
        with _LOCK:
            if _IMPL is None:
                ext_manager = extension.ExtensionManager("database.migration")
                _IMPL = {}
                for ext in ext_manager:
                    _IMPL[ext.name] = ext.obj if ext.obj else ext.plugin

    if project is not None:
        return [_IMPL[project]]
    else:
        return [one for one in _IMPL.values()]


def db_sync(version=None,  project=None):
    """Migrate the database to `version` or the most recent version."""
    backends = get_backend(project)
    for one in backends:
        one.db_sync(version)
