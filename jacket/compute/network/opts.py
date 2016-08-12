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

import jacket.compute.network
import jacket.compute.network.driver
import jacket.compute.network.floating_ips
import jacket.compute.network.ldapdns
import jacket.compute.network.linux_net
import jacket.compute.network.manager
import jacket.compute.network.neutronv2.api
import jacket.compute.network.rpcapi
import jacket.compute.network.security_group.openstack_driver


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             jacket.compute.network._network_opts,
             jacket.compute.network.driver.driver_opts,
             jacket.compute.network.floating_ips.floating_opts,
             jacket.compute.network.ldapdns.ldap_dns_opts,
             jacket.compute.network.linux_net.linux_net_opts,
             jacket.compute.network.manager.network_opts,
             jacket.compute.network.rpcapi.rpcapi_opts,
             jacket.compute.network.security_group.openstack_driver.security_group_opts,
         )),
        ('neutron', jacket.compute.network.neutronv2.api.neutron_opts),
        ('upgrade_levels',
         itertools.chain(
             [jacket.compute.network.rpcapi.rpcapi_cap_opt],
         )),
    ]
