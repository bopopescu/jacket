# Copyright 2015 OpenStack Foundation
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

from oslo_config import cfg

auth_opts = [
    cfg.BoolOpt('api_rate_limit',
                default=False,
                help='Whether to use per-user rate limiting for the api. '
                     'This option is only used by v2 api. Rate limiting '
                     'is removed from v2.1 api.'),
    cfg.StrOpt("auth_strategy",
            default="keystone",
            choices=("keystone", "noauth2"),
            help="""
This determines the strategy to use for authentication: keystone or noauth2.
'noauth2' is designed for testing only, as it does no actual credential
checking. 'noauth2' provides administrative credentials only if 'admin' is
specified as the username.
"""),
    cfg.BoolOpt("use_forwarded_for",
            default=False,
            help="""
When True, the 'X-Forwarded-For' header is treated as the canonical remote
address. When False (the default), the 'remote_address' header is used.

You should only enable this if you have an HTML sanitizing proxy.
"""),

    cfg.IntOpt('osapi_max_limit',
               default=1000,
               help='The maximum number of items that a collection '
                    'resource returns in a single response'),
]

ALL_OPTS = (auth_opts)


def register_opts(conf):
    conf.register_opts(ALL_OPTS)


def list_opts():
    # TODO(macsz) add opt group
    return {"DEFAULT": ALL_OPTS}
