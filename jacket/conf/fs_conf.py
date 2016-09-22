# Copyright (c) 2016 OpenStack Foundation
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
from jacket.i18n import _


# these options define baseline defaults that apply to all clients
default_clients_opts = [
    cfg.IntOpt('client_retry_limit',
               default=2,
               help=_('Number of times to retry when a client encounters an '
                      'expected intermittent error. Set to 0 to disable '
                      'retries.')),
]

clients_opts = [
    cfg.IntOpt('wait_retries',
               default=300,
               help='Number of times to retry when waiting.'),
    cfg.IntOpt('wait_retries_interval',
               default=2,
               help='Waiting time interval (seconds) between '
                    'retries on failures'),
    cfg.StrOpt('ca_file',
               help=_('Optional CA cert file to use in SSL connections.')),
    cfg.StrOpt('cert_file',
               help=_('Optional PEM-formatted certificate chain file.')),
    cfg.StrOpt('key_file',
               help=_('Optional PEM-formatted file that contains the '
                      'private key.')),
    cfg.BoolOpt('insecure',
                default=True,
                help=_("If set, then the server's certificate will not "
                       "be verified.")),
    cfg.IntOpt('timeout',
               help='https timeout'),
]

client_http_log_debug_opts = [
    cfg.BoolOpt('http_log_debug',
                default=True,
                help=_("Allow client's debug log output."))]


hybrid_cloud_agent_opts = [
    cfg.StrOpt('tunnel_cidr', help='tunnel_cidr', default='172.28.48.0/24'),
    cfg.StrOpt('route_gw', help='route_gw', default='172.28.48.254'),
    cfg.StrOpt('personality_path', help='config file path for hybrid cloud agent',
               default='/media/metadata/userdata.txt'),
    cfg.StrOpt('rabbit_host_ip', help='rabbit host ip for hybrid cloud agent to connect with', default='172.28.0.12'),
    cfg.StrOpt('rabbit_host_user_id', help='rabbit_host_user_id'),
    cfg.StrOpt('rabbit_host_user_password', help='password of rabbit user of the rabbit host which for hybrid '
                                                 'cloud agent to connect with')
]


def register_opts(conf):
    for client in ('fs_nova', 'fs_glance', 'fs_cinder'):
        client_specific_group = 'clients_' + client
        conf.register_opts(clients_opts, group=client_specific_group)
        conf.register_opts(client_http_log_debug_opts,
                           group=client_specific_group)

    conf.register_opts(default_clients_opts,
                       group='fs_clients')

    conf.register_opts(hybrid_cloud_agent_opts, 'hybrid_cloud_agent_opts')


def list_opts():
    for client in ('fs_nova', 'fs_glance', 'fs_cinder'):
        client_specific_group = 'clients_' + client
        yield client_specific_group, clients_opts
        yield client_specific_group, client_http_log_debug_opts

    yield 'fs_clients', default_clients_opts
    yield  'hybrid_cloud_agent_opts', hybrid_cloud_agent_opts
