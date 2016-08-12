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

import jacket.api.compute.auth
import jacket.api.compute.metadata.base
import jacket.api.compute.metadata.handler
import jacket.api.compute.metadata.vendordata_json
import jacket.api.compute.openstack
import jacket.api.compute.openstack.common
import jacket.api.compute.openstack.compute
import jacket.api.compute.openstack.compute.hide_server_addresses
import jacket.api.compute.openstack.compute.legacy_v2.contrib
import jacket.api.compute.openstack.compute.legacy_v2.contrib.fping
import jacket.api.compute.openstack.compute.legacy_v2.contrib.os_tenant_networks
import jacket.api.compute.openstack.compute.legacy_v2.extensions
import jacket.api.compute.openstack.compute.legacy_v2.servers
import jacket.compute.availability_zones
import jacket.compute.baserpc
import jacket.compute.cells.manager
import jacket.compute.cells.messaging
import jacket.compute.cells.opts
import jacket.compute.cells.rpc_driver
import jacket.compute.cells.rpcapi
import jacket.compute.cells.scheduler
import jacket.compute.cells.state
import jacket.compute.cells.weights.mute_child
import jacket.compute.cells.weights.ram_by_instance_type
import jacket.compute.cells.weights.weight_offset
import jacket.compute.cert.rpcapi
import jacket.compute.cloudpipe.pipelib
import jacket.cmd.compute.novnc
import jacket.cmd.compute.novncproxy
import jacket.cmd.compute.serialproxy
import jacket.cmd.compute.spicehtml5proxy
import jacket.compute.compute.api
import jacket.compute.compute.flavors
import jacket.compute.compute.manager
import jacket.compute.compute.monitors
import jacket.compute.compute.resource_tracker
import jacket.compute.compute.rpcapi
import jacket.compute.conductor.api
import jacket.compute.conductor.rpcapi
import jacket.compute.conductor.tasks.live_migrate
import jacket.compute.console.manager
import jacket.compute.console.rpcapi
import jacket.compute.console.serial
import jacket.compute.console.xvp
import jacket.compute.consoleauth
import jacket.compute.consoleauth.manager
import jacket.compute.consoleauth.rpcapi
import jacket.compute.crypto
import jacket.db.compute.api
import jacket.db.compute.base
import jacket.db.compute.sqlalchemy.api
import jacket.compute.exception
import jacket.compute.image.download.file
import jacket.compute.image.glance
import jacket.compute.ipv6.api
import jacket.compute.keymgr
import jacket.compute.keymgr.barbican
import jacket.compute.keymgr.conf_key_mgr
import jacket.compute.netconf
import jacket.compute.network
import jacket.compute.network.driver
import jacket.compute.network.floating_ips
import jacket.compute.network.ldapdns
import jacket.compute.network.linux_net
import jacket.compute.network.manager
import jacket.compute.network.neutronv2.api
import jacket.compute.network.rpcapi
import jacket.compute.network.security_group.openstack_driver
import jacket.compute.notifications
import jacket.objects.compute.network
import jacket.compute.paths
import jacket.compute.pci.request
import jacket.compute.pci.whitelist
import jacket.compute.quota
import jacket.compute.rdp
import jacket.compute.scheduler.driver
import jacket.compute.scheduler.filter_scheduler
import jacket.compute.scheduler.filters.aggregate_image_properties_isolation
import jacket.compute.scheduler.filters.core_filter
import jacket.compute.scheduler.filters.disk_filter
import jacket.compute.scheduler.filters.io_ops_filter
import jacket.compute.scheduler.filters.isolated_hosts_filter
import jacket.compute.scheduler.filters.num_instances_filter
import jacket.compute.scheduler.filters.ram_filter
import jacket.compute.scheduler.filters.trusted_filter
import jacket.compute.scheduler.host_manager
import jacket.compute.scheduler.ironic_host_manager
import jacket.compute.scheduler.manager
import jacket.compute.scheduler.rpcapi
import jacket.compute.scheduler.scheduler_options
import jacket.compute.scheduler.utils
import jacket.compute.scheduler.weights.io_ops
import jacket.compute.scheduler.weights.metrics
import jacket.compute.scheduler.weights.ram
import jacket.compute.service
import jacket.compute.servicegroup.api
import jacket.compute.spice
import jacket.compute.utils
import jacket.compute.vnc
import jacket.compute.vnc.xvp_proxy
import jacket.compute.volume
import jacket.compute.volume.cinder
import jacket.wsgi.compute


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             [jacket.api.compute.metadata.vendordata_json.file_opt],
             [jacket.api.compute.openstack.compute.allow_instance_snapshots_opt],
             jacket.api.compute.auth.auth_opts,
             jacket.api.compute.metadata.base.metadata_opts,
             jacket.api.compute.metadata.handler.metadata_opts,
             jacket.api.compute.openstack.common.osapi_opts,
             jacket.api.compute.openstack.compute.legacy_v2.contrib.ext_opts,
             jacket.api.compute.openstack.compute.legacy_v2.contrib.fping.fping_opts,
             jacket.api.compute.openstack.compute.legacy_v2.contrib.os_tenant_networks.
                 os_network_opts,
             jacket.api.compute.openstack.compute.legacy_v2.extensions.ext_opts,
             jacket.api.compute.openstack.compute.hide_server_addresses.opts,
             jacket.api.compute.openstack.compute.legacy_v2.servers.server_opts,
         )),
        ('neutron', jacket.api.compute.metadata.handler.metadata_proxy_opts),
        ('osapi_v21', jacket.api.compute.openstack.api_opts),
    ]
