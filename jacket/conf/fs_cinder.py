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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

fs_cinder_group = cfg.OptGroup(
    'fs_cinder',
    title='fs Cinder Options',
    help="Configuration options for the block storage")

fs_cinder_opts = [
    cfg.StrOpt('default_version',
               default='2',
               choices=['1', '2'],
               help="""
cinder client version
Possible values:
1,2
"""),
    cfg.IntOpt('http_retries',
               default=3,
               min=0,
               help="""
Number of times cinderclient should retry on any failed http call.
0 means connection is attempted only once. Setting it to any positive integer
means that on failure connection is retried that many times e.g. setting it
to 3 means total attempts to connect will be 4.

Possible values:

* Any integer value. 0 means connection is attempted only once
"""),
    cfg.IntOpt('num_retries',
               default=0,
               help='Number of retries when volume is opted.'),
    cfg.BoolOpt('cross_az_attach',
                default=True,
                help="""
Allow attach between instance and volume in different availability zones.

If False, volumes attached to an instance must be in the same availability
zone in Cinder as the instance availability zone in Nova.
This also means care should be taken when booting an instance from a volume
where source is not "volume" because Nova will attempt to create a volume using
the same availability zone as what is assigned to the instance.
If that AZ is not in Cinder (or allow_availability_zone_fallback=False in
cinder.conf), the volume create request will fail and the instance will fail
the build request.
By default there is no availability zone restriction on volume attach.
"""),
]

deprecated = {'timeout': [cfg.DeprecatedOpt('http_timeout',
                                            group=fs_cinder_group.name)],
              'cafile': [cfg.DeprecatedOpt('ca_certificates_file',
                                           group=fs_cinder_group.name)],
              'insecure': [cfg.DeprecatedOpt('api_insecure',
                                             group=fs_cinder_group.name)]}


def register_opts(conf):
    conf.register_group(fs_cinder_group)
    conf.register_opts(fs_cinder_opts, group=fs_cinder_group)
    ks_loading.register_session_conf_options(conf,
                                             fs_cinder_group.name,
                                             deprecated_opts=deprecated)


def list_opts():
    return {
        fs_cinder_group.name: fs_cinder_opts
    }
