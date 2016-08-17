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
    __import__('jacket.objects.compute.agent')
    __import__('jacket.objects.compute.aggregate')
    __import__('jacket.objects.compute.bandwidth_usage')
    __import__('jacket.objects.compute.block_device')
    __import__('jacket.objects.compute.build_request')
    __import__('jacket.objects.compute.cell_mapping')
    __import__('jacket.objects.compute.compute_node')
    __import__('jacket.objects.compute.dns_domain')
    __import__('jacket.objects.compute.ec2')
    __import__('jacket.objects.compute.external_event')
    __import__('jacket.objects.compute.fixed_ip')
    __import__('jacket.objects.compute.flavor')
    __import__('jacket.objects.compute.floating_ip')
    __import__('jacket.objects.compute.host_mapping')
    __import__('jacket.objects.compute.hv_spec')
    __import__('jacket.objects.compute.image_meta')
    __import__('jacket.objects.compute.instance')
    __import__('jacket.objects.compute.instance_action')
    __import__('jacket.objects.compute.instance_fault')
    __import__('jacket.objects.compute.instance_group')
    __import__('jacket.objects.compute.instance_info_cache')
    __import__('jacket.objects.compute.instance_mapping')
    __import__('jacket.objects.compute.instance_numa_topology')
    __import__('jacket.objects.compute.instance_pci_requests')
    __import__('jacket.objects.compute.keypair')
    __import__('jacket.objects.compute.migrate_data')
    __import__('jacket.objects.compute.migration')
    __import__('jacket.objects.compute.migration_context')
    __import__('jacket.objects.compute.monitor_metric')
    __import__('jacket.objects.compute.network')
    __import__('jacket.objects.compute.network_request')
    __import__('jacket.objects.compute.notification')
    __import__('jacket.objects.compute.numa')
    __import__('jacket.objects.compute.pci_device')
    __import__('jacket.objects.compute.pci_device_pool')
    __import__('jacket.objects.compute.request_spec')
    __import__('jacket.objects.compute.resource_provider')
    __import__('jacket.objects.compute.tag')
    __import__('jacket.objects.compute.quotas')
    __import__('jacket.objects.compute.security_group')
    __import__('jacket.objects.compute.security_group_rule')
    __import__('jacket.objects.compute.service')
    __import__('jacket.objects.compute.task_log')
    __import__('jacket.objects.compute.vcpu_model')
    __import__('jacket.objects.compute.virt_cpu_topology')
    __import__('jacket.objects.compute.virtual_interface')
    __import__('jacket.objects.compute.volume_usage')
