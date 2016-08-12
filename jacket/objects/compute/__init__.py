#    Copyright 2013 IBM Corp.
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

# NOTE(comstud): You may scratch your head as you see code that imports
# this module and then accesses attributes for objects such as Instance,
# etc, yet you do not see these attributes in here. Never fear, there is
# a little bit of magic. When objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.


def register_all():
    # NOTE(danms): You must make sure your object gets imported in this
    # function in order for it to be registered by services that may
    # need to receive it via RPC.
    __import__('compute.objects.agent')
    __import__('compute.objects.aggregate')
    __import__('compute.objects.bandwidth_usage')
    __import__('compute.objects.block_device')
    __import__('compute.objects.build_request')
    __import__('compute.objects.cell_mapping')
    __import__('compute.objects.compute_node')
    __import__('compute.objects.dns_domain')
    __import__('compute.objects.ec2')
    __import__('compute.objects.external_event')
    __import__('compute.objects.fixed_ip')
    __import__('compute.objects.flavor')
    __import__('compute.objects.floating_ip')
    __import__('compute.objects.host_mapping')
    __import__('compute.objects.hv_spec')
    __import__('compute.objects.image_meta')
    __import__('compute.objects.instance')
    __import__('compute.objects.instance_action')
    __import__('compute.objects.instance_fault')
    __import__('compute.objects.instance_group')
    __import__('compute.objects.instance_info_cache')
    __import__('compute.objects.instance_mapping')
    __import__('compute.objects.instance_numa_topology')
    __import__('compute.objects.instance_pci_requests')
    __import__('compute.objects.keypair')
    __import__('compute.objects.migrate_data')
    __import__('compute.objects.migration')
    __import__('compute.objects.migration_context')
    __import__('compute.objects.monitor_metric')
    __import__('compute.objects.network')
    __import__('compute.objects.network_request')
    __import__('compute.objects.notification')
    __import__('compute.objects.numa')
    __import__('compute.objects.pci_device')
    __import__('compute.objects.pci_device_pool')
    __import__('compute.objects.request_spec')
    __import__('compute.objects.resource_provider')
    __import__('compute.objects.tag')
    __import__('compute.objects.quotas')
    __import__('compute.objects.security_group')
    __import__('compute.objects.security_group_rule')
    __import__('compute.objects.service')
    __import__('compute.objects.task_log')
    __import__('compute.objects.vcpu_model')
    __import__('compute.objects.virt_cpu_topology')
    __import__('compute.objects.virtual_interface')
    __import__('compute.objects.volume_usage')
