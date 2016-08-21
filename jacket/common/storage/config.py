# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2012 Red Hat, Inc.
# Copyright 2013 NTT corp.
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

"""Command-line flag library.

Emulates gflags by wrapping cfg.ConfigOpts.

The idea is to move fully to cfg eventually, and this wrapper is a
stepping stone.

"""

import socket

from oslo_config import cfg
from oslo_log import log as logging
from oslo_middleware import cors

from jacket.common import config


CONF = config.CONF
# logging.register_options(CONF)

core_opts = []

debug_opts = [
]

CONF.register_cli_opts(core_opts)
CONF.register_cli_opts(debug_opts)

def set_middleware_defaults():
    """Update default configuration options for oslo.middleware."""
    # CORS Defaults
    # TODO(krotscheck): Update with https://review.openstack.org/#/c/285368/
    cfg.set_defaults(cors.CORS_OPTS,
                     allow_headers=['X-Auth-Token',
                                    'X-Identity-Status',
                                    'X-Roles',
                                    'X-Service-Catalog',
                                    'X-User-Id',
                                    'X-Tenant-Id',
                                    'X-OpenStack-Request-ID',
                                    'X-Trace-Info',
                                    'X-Trace-HMAC',
                                    'OpenStack-API-Version'],
                     expose_headers=['X-Auth-Token',
                                     'X-Subject-Token',
                                     'X-Service-Token',
                                     'X-OpenStack-Request-ID',
                                     'OpenStack-API-Version'],
                     allow_methods=['GET',
                                    'PUT',
                                    'POST',
                                    'DELETE',
                                    'PATCH',
                                    'HEAD']
                     )
