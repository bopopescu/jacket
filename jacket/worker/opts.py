# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

import jacket.compute.cloud.flavors
import jacket.compute.cloud.manager
import jacket.compute.cloud.monitors
import jacket.compute.cloud.resource_tracker
import jacket.compute.cloud.rpcapi
import jacket.compute.conf


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             jacket.compute.cloud.flavors.flavor_opts,
             jacket.compute.cloud.manager.compute_opts,
             jacket.compute.cloud.manager.instance_cleaning_opts,
             jacket.compute.cloud.manager.interval_opts,
             jacket.compute.cloud.manager.running_deleted_opts,
             jacket.compute.cloud.manager.timeout_opts,
             jacket.compute.cloud.monitors.compute_monitors_opts,
             jacket.compute.cloud.resource_tracker.resource_tracker_opts,
             jacket.compute.cloud.resource_tracker.allocation_ratio_opts,
             jacket.compute.cloud.rpcapi.rpcapi_opts,
         )),
        ('upgrade_levels',
         itertools.chain(
             [jacket.compute.cloud.rpcapi.rpcapi_cap_opt],
         )),
    ]
