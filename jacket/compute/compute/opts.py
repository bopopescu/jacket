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

import jacket.compute.compute.flavors
import jacket.compute.compute.manager
import jacket.compute.compute.monitors
import jacket.compute.compute.resource_tracker
import jacket.compute.compute.rpcapi
import jacket.compute.conf


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             jacket.compute.compute.flavors.flavor_opts,
             jacket.compute.compute.manager.compute_opts,
             jacket.compute.compute.manager.instance_cleaning_opts,
             jacket.compute.compute.manager.interval_opts,
             jacket.compute.compute.manager.running_deleted_opts,
             jacket.compute.compute.manager.timeout_opts,
             jacket.compute.compute.monitors.compute_monitors_opts,
             jacket.compute.compute.resource_tracker.resource_tracker_opts,
             jacket.compute.compute.resource_tracker.allocation_ratio_opts,
             jacket.compute.compute.rpcapi.rpcapi_opts,
         )),
        ('upgrade_levels',
         itertools.chain(
             [jacket.compute.compute.rpcapi.rpcapi_cap_opt],
         )),
    ]
