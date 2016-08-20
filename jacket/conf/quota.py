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


from oslo_config import cfg

quota_opts = [
    cfg.IntOpt('reservation_expire',
               default=86400,
               help='Number of seconds until a reservation expires'),

    cfg.IntOpt('until_refresh',
               min=0,
               default=0,
               help="""
The count of reservations until usage is refreshed. This defaults to 0 (off) to
avoid additional load but it is useful to turn on to help keep quota usage
up-to-date and reduce the impact of out of sync usage issues.

Possible values:

 * 0 (default) or any positive integer.
"""),
    cfg.IntOpt('max_age',
               default=0,
               help='Number of seconds between subsequent usage refreshes. '
                    'This defaults to 0(off) to avoid additional load but it '
                    'is useful to turn on to help keep quota usage up to date '
                    'and reduce the impact of out of sync usage issues. '
                    'Note that quotas are not updated on a periodic task, '
                    'they will update on a new reservation if max_age has '
                    'passed since the last reservation'),
    ]


def register_opts(conf):
    conf.register_opts(quota_opts)


# TODO(pumaranikar): We can consider moving these options to quota group
# and renaming them all to drop the quota bit.
def list_opts():
    return {'DEFAULT': quota_opts}
