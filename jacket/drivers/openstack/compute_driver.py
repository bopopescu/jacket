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

"""
Driver base-classes:

    (Beginning of) the contract that compute drivers must follow, and shared
    types that support that contract
"""

import copy
import socket
import traceback

from oslo_log import log as logging
from oslo_serialization import jsonutils
from oslo_utils import excutils
from oslo_utils import strutils

from jacket.compute.cloud import power_state
from jacket.compute.cloud import task_states
from jacket.compute.cloud import vm_states
from jacket.compute.virt import driver
from jacket.compute.virt import hardware
from jacket import conf
from jacket import context as req_context
from jacket.compute import image
from jacket.db.extend import api as caa_db_api
from jacket.drivers.openstack import base
from jacket.drivers.openstack import exception_ex
from jacket import exception
from jacket.i18n import _LE
from jacket import utils
from jacket.objects import compute as objects

LOG = logging.getLogger(__name__)

CONF = conf.CONF

FS_DOMAIN_NOSTATE = 0
FS_DOMAIN_RUNNING = 1
FS_DOMAIN_BLOCKED = 2
FS_DOMAIN_PAUSED = 3
FS_DOMAIN_SHUTDOWN = 4
FS_DOMAIN_SHUTOFF = 5
FS_DOMAIN_CRASHED = 6
FS_DOMAIN_PMSUSPENDED = 7

FS_POWER_STATE = {
    FS_DOMAIN_NOSTATE: power_state.NOSTATE,
    FS_DOMAIN_RUNNING: power_state.RUNNING,
    FS_DOMAIN_BLOCKED: power_state.RUNNING,
    FS_DOMAIN_PAUSED: power_state.PAUSED,
    FS_DOMAIN_SHUTDOWN: power_state.SHUTDOWN,
    FS_DOMAIN_SHUTOFF: power_state.SHUTDOWN,
    FS_DOMAIN_CRASHED: power_state.CRASHED,
    FS_DOMAIN_PMSUSPENDED: power_state.SUSPENDED,
}


class OsComputeDriver(driver.ComputeDriver, base.OsDriver):
    def __init__(self, virtapi):
        self._os_novaclient = None
        self._os_cinderclient = None
        self._os_glanceclient = None
        self.caa_db_api = caa_db_api
        self._image_api = image.API()
        super(OsComputeDriver, self).__init__(virtapi)

    def after_detach_volume_fail(self, job_detail_info, **kwargs):
        pass

    def after_detach_volume_success(self, job_detail_info, **kwargs):
        pass

    def _add_tag_to_metadata(self, metadata, caa_instance_id):
        if not metadata:
            metadata = {}

        metadata['tag:caa_instance_id'] = caa_instance_id
        return metadata

    def _is_booted_from_volume(self, instance, disk_mapping=None):
        """Determines whether the VM is booting from volume

        Determines whether the disk mapping indicates that the VM
        is booting from a volume.
        """
        return (not bool(instance.get('image_ref')))

    def _transfer_to_sub_block_device_mapping_v2(self, context, instance,
                                                 block_device_mapping):
        """

        :param block_device_mapping:
        {
            'block_device_mapping': [{
                'guest_format': None,
                'boot_index': 0,
                'mount_device': u'/dev/sda',
                'connection_info': {
                    u'driver_volume_type': u'fs_clouds_volume',
                    'serial': u'817492df-3e7f-439a-bfb3-6c2f6488a6e5',
                    u'data': {
                        u'access_mode': u'rw',
                        u'qos_specs': None,
                        u'display_name': u'image-v-02',
                        u'volume_id': u'817492df-3e7f-439a-bfb3-6c2f6488a6e5',
                        u'backend': u'fsclouds'
                    }
                },
                'disk_bus': None,
                'device_type': None,
                'delete_on_termination': False
            }],
            'root_device_name': u'/dev/sda',
            'ephemerals': [],
            'swap': None
        }
        :return: type list, [{
                            "boot_index": 0,
                            "uuid": "5e9ba941-7fad-4515-872a-0b2f1a05d577",
                            "volume_size": "1",
                            "device_name": "/dev/sda",
                            "source_type": "volume",
                            "volume_id": "5e9ba941-7fad-4515-872a-0b2f1a05d577",
                            "delete_on_termination": "False"}]
        """
        sub_bdms = []
        bdm_list = block_device_mapping.get('block_device_mapping', [])
        for bdm in bdm_list:
            bdm_info_dict = {}
            # bdm_info_dict['delete_on_termination'] = bdm.get(
            #    'delete_on_termination', False)
            bdm_info_dict['boot_index'] = bdm.get('boot_index')
            bdm_info_dict['destination_type'] = 'volume'

            source_type = bdm.get('source_type', None)
            # NOTE(laoyi) Now, only support image and blank
            if source_type == 'image':
                image_id = bdm.get('image_id', None)
                if image_id:
                    provider_image_id = self._get_provider_image_id(context,
                                                                    image_id)
                else:
                    provider_image_id = self._get_provider_base_image_id(
                        context)
                if provider_image_id:
                    bdm_info_dict['source_type'] = 'image'
                    bdm_info_dict['uuid'] = provider_image_id
                else:
                    bdm_info_dict['source_type'] = 'blank'

                bdm_info_dict['volume_size'] = str(bdm.get('size'))
                bdm_info_dict['delete_on_termination'] = bdm.get(
                    'delete_on_termination', False)
            elif source_type == 'blank':
                bdm_info_dict['source_type'] = source_type
                bdm_info_dict['volume_size'] = str(bdm.get('size'))
                bdm_info_dict['delete_on_termination'] = bdm.get(
                    'delete_on_termination', False)
            else:
                volume_id = bdm.get('connection_info').get('data').get(
                    'volume_id')
                if volume_id:
                    provider_volume = self._get_provider_volume(context,
                                                                volume_id)
                    bdm_info_dict['uuid'] = provider_volume.id
                    bdm_info_dict['volume_size'] = str(provider_volume.size)
                    # bdm_info_dict['device_name'] = device_name
                    bdm_info_dict['source_type'] = 'volume'
                    bdm_info_dict['delete_on_termination'] = False
                else:
                    # TODO: need to support snapshot id
                    continue

            sub_bdms.append(bdm_info_dict)

        if not sub_bdms:
            sub_bdms = None

        return sub_bdms

    def _get_provider_security_groups_list(self, context, project_mapper=None):
        if project_mapper is None:
            project_mapper = self._get_project_mapper(context,
                                                      context.project_id)

        provider_sg = project_mapper.get('security_groups', None)
        if provider_sg:
            security_groups = provider_sg.split(',')
        else:
            security_groups = None

        return security_groups

    def _get_provider_nics(self, context, project_mapper=None):
        if project_mapper is None:
            project_mapper = self._get_project_mapper(context,
                                                      context.project_id)
        provider_net_data = project_mapper.get('net_data', None)
        provider_net_api = project_mapper.get('net_api', None)
        provider_net_external = project_mapper.get('net_external', None)
        nics = []
        if provider_net_external:
            nics.append({'net-id': provider_net_external})
        nics.append({'net-id': provider_net_data})
        nics.append({'net-id': provider_net_api})

        return nics

    def _get_agent_inject_file(self, instance, driver_param_inject_files):
        return dict(driver_param_inject_files)

    def _generate_provider_instance_name(self, instance_name, instance_id):
        """

        :param instance_name: type string
        :param instance_id: type string
        :return: type string, e.g. 'my_vm@97988012-4f48-4463-a150-d7e6b0a321d9'
        """
        if not instance_name:
            instance_name = 'server'
        return '@'.join([instance_name, instance_id])

    def _get_provider_flavor_id(self, context, flavor_id):

        # get dest flavor id
        flavor_mapper = self.caa_db_api.flavor_mapper_get(context,
                                                          flavor_id,
                                                          context.project_id)

        dest_flavor_id = flavor_mapper.get("dest_flavor_id", flavor_id)

        return dest_flavor_id

    def _create_snapshot_metadata(self, image_meta, instance,
                                  img_fmt, snp_name):
        metadata = {'is_public': False,
                    'status': 'active',
                    'name': snp_name,
                    'properties': {
                        'kernel_id': instance.kernel_id,
                        'image_location': 'snapshot',
                        'image_state': 'available',
                        'owner_id': instance.project_id,
                        'ramdisk_id': instance.ramdisk_id,
                    }
                    }
        if instance.os_type:
            metadata['properties']['os_type'] = instance.os_type

        if img_fmt:
            metadata['disk_format'] = img_fmt
        else:
            metadata['disk_format'] = image_meta.disk_format

        if image_meta.obj_attr_is_set("container_format"):
            metadata['container_format'] = image_meta.container_format
        else:
            metadata['container_format'] = "bare"

        return metadata

    def list_instance_uuids(self):
        uuids = []
        context = req_context.RequestContext(is_admin=True,
                                             project_id='default')
        servers = self.os_novaclient(context).list()
        for server in servers:
            server_id = server.id
            uuids.append(server_id)

        LOG.debug('list_instance_uuids: %s' % uuids)
        return uuids

    def list_instances(self):
        """List VM instances from all nodes.
        :return: list of instance id. e.g.['id_001', 'id_002', ...]
        """

        instances = []
        context = req_context.RequestContext(is_admin=True,
                                             project_id='default')
        servers = self.os_novaclient(context).list()
        for server in servers:
            server_name = server.name
            instances.append(server_name)

        LOG.debug('list_instance: %s' % instances)
        return instances

    def list_instances_stats(self):
        """List VM instances from all nodes.
        :return: list of instance id. e.g.['id_001', 'id_002', ...]
        """
        stats = {}
        context = req_context.RequestContext(is_admin=True,
                                             project_id='default')
        servers = self.os_novaclient(context).list()
        for server in servers:
            uuid = server.uuid
            stats[uuid] = server.state

        return stats

    def get_console_output(self, context, instance):
        provider_uuid = self._get_provider_instance_id(context, instance.uuid)
        return self.os_novaclient(context).get_console_output(provider_uuid)

    def volume_create(self, context, instance):
        size = instance.get_flavor().get('root_gb')
        volume_name = instance.uuid
        self.os_cinderclient(context).create_volume(size,
                                                    display_name=volume_name)
        volume = self.os_cinderclient(context).get_volume_by_name(volume_name)
        self.os_cinderclient(context).check_create_volume_complete(volume.id)

        return volume

    def volume_delete(self, context, instance):
        volume_name = instance.uuid
        volume = self.os_cinderclient(context).get_volume_by_name(volume_name)
        if volume:
            if volume.status != "deleting":
                self.os_cinderclient(context).delete_volume(volume)
            self.os_cinderclient(context).check_delete_volume_complete(
                volume.id)

    def _attach_volume(self, context, instance, provider_volume, mountpoint):
        provider_server = self._get_provider_instance(context, instance)
        if not provider_server:
            LOG.error('Can not find server in provider os, '
                      'server: %s' % instance.uuid)
            raise exception_ex.ServerNotExistException(
                server_name=instance.display_name)

        if provider_volume.status == "in-use":
            attach_id, server_id = self._get_attachment_id_for_volume(
                provider_volume)
            if server_id != provider_server.id:
                LOG.error(_LE("provider volume(%s) has been attached to "
                              "provider instance(%s)"), provider_volume.id,
                          server_id)
                raise exception_ex.VolumeAttachFailed(
                    volume_id=provider_volume.id)
            else:
                return

        if provider_volume.status == 'available':
            self.os_novaclient(context).attach_volume(provider_server.id,
                                                      provider_volume.id,
                                                      mountpoint)
            self.os_cinderclient(context).check_attach_volume_complete(
                provider_volume)
        else:
            raise Exception('provider volume %s is not available, '
                            'status is %s' %
                            (provider_volume.id,
                             provider_volume.status))

    def attach_volume(self, context, connection_info, instance, mountpoint=None,
                      disk_bus=None, device_type=None,
                      encryption=None):
        """

        :param context:
            ['auth_token',
            'elevated',
            'from_dict',
            'instance_lock_checked',
            'is_admin',
            'project_id',
            'project_name',
            'quota_class',
            'read_deleted',
            'remote_address',
            'request_id',
            'roles',
            'service_catalog',
            'tenant',
            'timestamp',
            'to_dict',
            'update_store',
            'user',
            'user_id',
            'user_name']
        :param connection_info:
            {
                u'driver_volume_type': u'vcloud_volume',
                'serial': u'824d397e-4138-48e4-b00b-064cf9ef4ed8',
                u'data': {
                    u'access_mode': u'rw',
                    u'qos_specs': None,
                    u'display_name': u'volume_02',
                    u'volume_id': u'824d397e-4138-48e4-b00b-064cf9ef4ed8',
                    u'backend': u'vcloud'
                }
            }
        :param instance:
        Instance(
            access_ip_v4=None,
            access_ip_v6=None,
            architecture=None,
            auto_disk_config=False,
            availability_zone='az01.hws--fusionsphere',
            cell_name=None,
            cleaned=False,
            config_drive='',
            created_at=2016-01-14T07: 17: 40Z,
            default_ephemeral_device=None,
            default_swap_device=None,
            deleted=False,
            deleted_at=None,
            disable_terminate=False,
            display_description='volume_backend_01',
            display_name='volume_backend_01',
            ephemeral_gb=0,
            ephemeral_key_uuid=None,
            fault=<?>,
            host='420824B8-AC4B-7A64-6B8D-D5ACB90E136A',
            hostname='volume-backend-01',
            id=57,
            image_ref='',
            info_cache=InstanceInfoCache,
            instance_type_id=2,
            kernel_id='',
            key_data=None,
            key_name=None,
            launch_index=0,
            launched_at=2016-01-14T07: 17: 43Z,
            launched_on='420824B8-AC4B-7A64-6B8D-D5ACB90E136A',
            locked=False,
            locked_by=None,
            memory_mb=512,
            metadata={

            },
            node='420824B8-AC4B-7A64-6B8D-D5ACB90E136A',
            numa_topology=<?>,
            os_type=None,
            pci_devices=<?>,
            power_state=0,
            progress=0,
            project_id='e178f1b9539b4a02a9c849dd7ea3ea9e',
            ramdisk_id='',
            reservation_id='r-marvoq8g',
            root_device_name='/dev/sda',
            root_gb=1,
            scheduled_at=None,
            security_groups=SecurityGroupList,
            shutdown_terminate=False,
            system_metadata={
                image_base_image_ref='',
                image_checksum='d972013792949d0d3ba628fbe8685bce',
                image_container_format='bare',
                image_disk_format='qcow2',
                image_image_id='617e72df-41ba-4e0d-ac88-cfff935a7dc3',
                image_image_name='cirros',
                image_min_disk='0',
                image_min_ram='0',
                image_size='13147648',
                instance_type_ephemeral_gb='0',
                instance_type_flavorid='1',
                instance_type_id='2',
                instance_type_memory_mb='512',
                instance_type_name='m1.tiny',
                instance_type_root_gb='1',
                instance_type_rxtx_factor='1.0',
                instance_type_swap='0',
                instance_type_vcpu_weight=None,
                instance_type_vcpus='1'
            },
            task_state=None,
            terminated_at=None,
            updated_at=2016-01-14T07: 17: 43Z,
            user_data=u'<SANITIZED>,
            user_id='d38732b0a8ff451eb044015e80bbaa65',
            uuid=9eef20f0-5ebf-4793-b4a2-5a667b0acad0,
            vcpus=1,
            vm_mode=None,
            vm_state='active')

        Volume object:
        {
            'status': u'attaching',
            'volume_type_id': u'type01',
            'volume_image_metadata': {
                u'container_format': u'bare',
                u'min_ram': u'0',
                u'disk_format': u'qcow2',
                u'image_name': u'cirros',
                u'image_id': u'617e72df-41ba-4e0d-ac88-cfff935a7dc3',
                u'checksum': u'd972013792949d0d3ba628fbe8685bce',
                u'min_disk': u'0',
                u'size': u'13147648'
            },
            'display_name': u'volume_02',
            'attachments': [],
            'attach_time': '',
            'availability_zone': u'az01.hws--fusionsphere',
            'bootable': True,
            'created_at': u'2016-01-18T07: 03: 57.822386',
            'attach_status': 'detached',
            'display_description': None,
            'volume_metadata': {
                u'readonly': u'False'
            },
            'shareable': u'false',
            'snapshot_id': None,
            'mountpoint': '',
            'id': u'824d397e-4138-48e4-b00b-064cf9ef4ed8',
            'size': 120
        }
        :param mountpoint: string. e.g. "/dev/sdb"
        :param disk_bus:
        :param device_type:
        :param encryption:
        :return:
        """
        LOG.debug('start to attach volume.')

        cascading_volume_id = connection_info['data']['volume_id']

        provider_volume = self._get_provider_volume(context,
                                                    cascading_volume_id)
        self._attach_volume(context, instance, provider_volume, mountpoint)

        LOG.debug('attach volume : %s success.' % cascading_volume_id)

    def destroy(self, context, instance, network_info, block_device_info=None,
                destroy_disks=True, migrate_data=None):
        """
        :param instance:
        :param network_info:
        :param block_device_info:
        :param destroy_disks:
        :param migrate_data:
        :return:
        """
        try:
            provider_server = self._get_provider_instance(context, instance)
        except exception.EntityNotFound:
            LOG.debug("instance is not exist, no need to delete!",
                      instance=instance)
            return

        if provider_server:
            self.os_novaclient(context).delete(provider_server)
            self.os_novaclient(context).check_delete_server_complete(
                provider_server)
        else:
            LOG.error('Can not found server to delete.')
            # raise exception_ex.ServerNotExistException(server_name=instance.display_name)

        try:
            provider_lxc_volume_id = instance.system_metadata.get(
                'provider_lxc_volume_id', None)
            provider_lxc_volume_del = instance.system_metadata.get(
                'provider_lxc_volume_del', False)
            provider_lxc_volume_del = strutils.bool_from_string(
                provider_lxc_volume_del, strict=True)

            if provider_lxc_volume_del and provider_lxc_volume_id:
                self.os_cinderclient(context).delete_volume(
                    provider_lxc_volume_id)
        except Exception:
            pass

        try:
            # delete instance mapper
            self.caa_db_api.instance_mapper_delete(context,
                                                   instance.uuid,
                                                   instance.project_id)
        except Exception as ex:
            LOG.error(_LE("instance_mapper_delete failed! ex = %s"), ex)

        LOG.debug('success to delete instance: %s' % instance.uuid)

    def _detach_volume(self, context, provider_volume):
        if provider_volume.status == "available":
            LOG.debug("provider volume(%s) has been detach", provider_volume.id)
            return

        attachment_id, server_id = self._get_attachment_id_for_volume(
            provider_volume)

        LOG.debug('server_id: %s' % server_id)
        LOG.debug('submit detach task')
        self.os_novaclient(context).detach_volume(server_id, provider_volume.id)

        LOG.debug('wait for volume in available status.')
        self.os_cinderclient(context).check_detach_volume_complete(
            provider_volume)

    def detach_volume(self, connection_info, instance, mountpoint,
                      encryption=None):
        LOG.debug('start to detach volume.')
        LOG.debug('instance: %s' % instance)
        LOG.debug('connection_info: %s' % connection_info)

        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)
        cascading_volume_id = connection_info['data']['volume_id']

        provider_volume = self._get_provider_volume(context,
                                                    cascading_volume_id)
        self._detach_volume(context, provider_volume)
        LOG.debug("detach volume success!", instance=instance)

    def get_available_nodes(self, refresh=False):
        """Returns nodenames of all nodes managed by the compute service.

        This method is for multi compute-nodes support. If a driver supports
        multi compute-nodes, this method returns a list of nodenames managed
        by the service. Otherwise, this method should return
        [hypervisor_hostname].
        """
        hostname = socket.gethostname()
        return [hostname]

    def _get_host_stats(self, hostname):
        return {'vcpus': 999999, 'vcpus_used': 0, 'memory_mb': 999999,
                'memory_mb_used': 0, 'local_gb': 99999999,
                'local_gb_used': 0, 'host_memory_total': 99999999,
                'disk_total': 99999999, 'host_memory_free': 99999999,
                'disk_used': 0, 'hypervisor_type': 'fusionsphere',
                'hypervisor_version': '5005000',
                'hypervisor_hostname': hostname,
                'cpu_info': '{"model": ["Intel(R) Xeon(R) CPU E5-2670 0 @ 2.60GHz"],'
                            '"vendor": ["Huawei Technologies Co., Ltd."], '
                            '"topology": {"cores": 16, "threads": 32}}',
                'supported_instances': jsonutils.dumps(
                    [["i686", "xen", "uml"], ["x86_64", "xen", "uml"]]),
                'numa_topology': None,}

    def get_available_resource(self, nodename):
        host_stats = self._get_host_stats(nodename)

        supported_instances = list()
        for one in jsonutils.loads(host_stats['supported_instances']):
            supported_instances.append((one[0], one[1], one[2]))

        return {'vcpus': host_stats['vcpus'],
                'memory_mb': host_stats['host_memory_total'],
                'local_gb': host_stats['disk_total'], 'vcpus_used': 0,
                'memory_mb_used': host_stats['host_memory_total'] - host_stats[
                    'host_memory_free'],
                'local_gb_used': host_stats['disk_used'],
                'hypervisor_type': host_stats['hypervisor_type'],
                'hypervisor_version': host_stats['hypervisor_version'],
                'hypervisor_hostname': host_stats['hypervisor_hostname'],
                'cpu_info': jsonutils.dumps(host_stats['cpu_info']),
                'supported_instances': supported_instances,
                'numa_topology': None,}

    def get_info(self, instance):
        STATUS = power_state.NOSTATE

        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)

        server = self._get_provider_instance(context, instance)
        LOG.debug('server: %s' % server)
        if server:
            instance_power_state = getattr(server, 'OS-EXT-STS:power_state')
            STATUS = FS_POWER_STATE[instance_power_state]
        LOG.debug('end to get_info: %s' % STATUS)

        return hardware.InstanceInfo(
            state=STATUS,
            max_mem_kb=0,
            mem_kb=0,
            num_cpu=1)

    def get_instance_macs(self, instance):
        """
        No need to implement.
        :param instance:
        :return:
        """
        pass

    def get_volume_connector(self, instance):
        return {'ip': CONF.my_block_storage_ip,
                'initiator': 'fake',
                'host': 'fakehost'}

    def init_host(self, host):
        pass

    def power_off(self, instance, timeout=0, retry_interval=0):

        LOG.debug('start to stop server: %s' % instance.uuid)
        server = self._get_provider_instance(hybrid_instance=instance)
        if not server:
            LOG.debug('can not find sub os server for '
                      'instance: %s' % instance.uuid)
            raise exception_ex.ServerNotExistException(
                server_name=instance.display_name)

        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)

        LOG.debug('server: %s status is: %s' % (server.id, server.status))
        if server.status == vm_states.ACTIVE.upper():
            LOG.debug('start to add stop task')
            server.stop()
            LOG.debug('submit stop task')
            self.os_novaclient(context).check_stop_server_complete(server)
            LOG.debug('stop server: %s success' % instance.uuid)
        elif server.status == 'SHUTOFF':
            LOG.debug('sub instance status is already STOPPED.')
            LOG.debug('stop server: %s success' % instance.uuid)
            return
        else:
            LOG.warning('server status is not in ACTIVE OR STOPPED,'
                        'can not do POWER_OFF operation')
            raise exception_ex.ServerStatusException(status=server.status)

    def power_on(self, context, instance, network_info,
                 block_device_info=None):

        LOG.debug('start to start server: %s' % instance.uuid)
        server = self._get_provider_instance(context, instance)
        if not server:
            LOG.debug('can not find sub os server for '
                      'instance: %s' % instance.uuid)
            raise exception_ex.ServerNotExistException(instance.display_name)

        LOG.debug('server: %s status is: %s' % (server.id, server.status))
        if server.status == 'SHUTOFF':
            LOG.debug('start to add start task')
            server.start()
            LOG.debug('submit start task')
            self.os_novaclient(context).check_start_server_complete(server)
            LOG.debug('start server: %s success' % instance.uuid)
        elif server.status == vm_states.ACTIVE.upper():
            LOG.debug('sub instance status is already ACTIVE.')
            return
        else:
            LOG.warning('server status is not in ACTIVE OR STOPPED,'
                        'can not do POWER_ON operation')
            raise exception_ex.ServerStatusException(status=server.status)

    def reboot(self, context, instance, network_info, reboot_type,
               block_device_info=None, bad_volumes_callback=None):

        LOG.debug('start to reboot server: %s' % instance.uuid)
        server = self._get_provider_instance(context, instance)
        if not server:
            LOG.debug('can not find sub os server for '
                      'instance: %s' % instance.uuid)
            raise exception_ex.ServerNotExistException(
                server_name=instance.display_name)

        LOG.debug('server: %s status is: %s' % (server.id, server.status))
        if server.status == vm_states.ACTIVE.upper():
            server.reboot(reboot_type)
            self.os_novaclient(context).check_reboot_server_complete(server)
            LOG.debug('reboot server: %s success' % instance.uuid)
        elif server.status == 'SHUTOFF':
            server.start()
            self.os_novaclient(context).check_start_server_complete(server)
            LOG.debug('reboot server: %s success' % instance.uuid)
        else:
            LOG.warning('server status is not in ACTIVE OR STOPPED,'
                        'can not do POWER_OFF operation')
            raise exception_ex.ServerStatusException(status=server.status)

    def provider_create_image(self, context, instance, image, metadata):
        provider_instance = self._get_provider_instance(context,
                                                        instance)

        provider_metadata = {
            "disk_format": metadata.get("disk_format", "raw"),
            "container_format": metadata.get("container_format", "bare")}

        # provider create image
        location, provider_image_id = self.os_novaclient(
            context).create_image(
            provider_instance, image['name'], provider_metadata)

        try:
            # wait create image success
            self.os_novaclient(context).check_create_image_server_complete(
                provider_instance)

            # wait image status is active
            self.os_glanceclient(context).check_image_active_complete(
                provider_image_id)
        except Exception as ex:
            LOG.exception(_LE("create image failed! ex = %s"), ex)
            with excutils.save_and_reraise_exception():
                self.os_glanceclient(context).delete(provider_image_id)

        return provider_instance, provider_image_id

    def snapshot(self, context, instance, image_id, update_task_state):

        snapshot = self._image_api.get(context, image_id)

        image_format = None

        metadata = self._create_snapshot_metadata(instance.image_meta,
                                                  instance,
                                                  image_format,
                                                  snapshot['name'])

        update_task_state(task_state=task_states.IMAGE_PENDING_UPLOAD)
        provider_instance, provider_image_id = self.provider_create_image(
            context, instance, snapshot, metadata)

        try:

            update_task_state(task_state=task_states.IMAGE_UPLOADING,
                              expected_state=task_states.IMAGE_PENDING_UPLOAD)

            try:
                image = self.os_glanceclient(context).get_image(
                    provider_image_id)
                LOG.debug("+++hw, image = %s", image)
                if hasattr(image, "direct_url"):
                    direct_url = image.direct_url
                    if direct_url.startswith("swift+http://") or \
                            direct_url.startswith("http://") or \
                            direct_url.startswith("https://"):

                        metadata["location"] = direct_url
                        self._image_api.update(context, image_id, metadata,
                                               purge_props=False)
                    else:
                        raise Exception()
                else:
                    raise Exception()
            except Exception:
                metadata.pop("location", None)
                # download from provider glance
                LOG.debug("+++hw, begin to download image(%s)",
                          provider_image_id)
                image_data = self.os_glanceclient(context).data(
                    provider_image_id)
                LOG.debug("+++hw, image length = %s", len(image_data))
                self._image_api.update(context,
                                       image_id,
                                       metadata,
                                       image_data)

            # create image mapper
            values = {"provider_image_id": provider_image_id}
            self.caa_db_api.image_mapper_create(context, image_id,
                                                context.project_id,
                                                values)
        except Exception as ex:
            LOG.exception(_LE("create image failed! ex = %s"), ex)
            with excutils.save_and_reraise_exception():
                self.os_glanceclient(context).delete(provider_image_id)

    def get_provider_lxc_volume_id(self, context, instance, index):
        lxc_volume_id = instance.system_metadata.get('provider_lxc_volume_id',
                                                     None)
        if lxc_volume_id:
            return lxc_volume_id

        provider_instance_uuid = self._get_provider_instance_id(
            context, instance.uuid)
        if provider_instance_uuid is None:
            return
        volumes = self.os_novaclient(context).get_server_volumes(
            provider_instance_uuid)
        volumes = sorted(volumes, key=lambda volume: volume.device)
        LOG.debug("+++hw, volumes = %s", volumes)
        lxc_volume = None
        if len(volumes) > index:
            lxc_volume = volumes[index]
        if lxc_volume is not None:
            return lxc_volume.volumeId

    def _spawn(self, context, instance, image_meta, injected_files,
               admin_password, network_info=None, block_device_info=None):
        try:
            LOG.debug('instance: %s' % instance)
            LOG.debug('block device info: %s' % block_device_info)

            flavor = instance.get_flavor()
            LOG.debug('flavor: %s' % flavor)

            sub_flavor_id = self._get_provider_flavor_id(context,
                                                         flavor.flavorid)

            name = self._generate_provider_instance_name(instance.display_name,
                                                         instance.uuid)
            LOG.debug('name: %s' % name)

            image_ref = None

            if instance.image_ref:
                sub_image_id = self._get_provider_base_image_id(context)
                try:
                    image_ref = self.os_glanceclient(context).get_image(
                        sub_image_id)
                except Exception as ex:
                    LOG.exception(_LE("get image(%(image_id)s) failed, "
                                      "ex = %(ex)s"), image_id=sub_image_id,
                                  ex=ex)
                    raise
            else:
                image_ref = None
            if instance.metadata:
                metadata = copy.deepcopy(instance.metadata)
            else:
                metadata = {}

            metadata = self._add_tag_to_metadata(metadata, instance.uuid)
            LOG.debug('metadata: %s' % metadata)

            app_security_groups = instance.security_groups
            LOG.debug('app_security_groups: %s' % app_security_groups)

            agent_inject_files = self._get_agent_inject_file(instance,
                                                             injected_files)

            sub_bdm = self._transfer_to_sub_block_device_mapping_v2(
                context, instance, block_device_info)
            LOG.debug('sub_bdm: %s' % sub_bdm)

            project_mapper = self._get_project_mapper(context,
                                                      context.project_id)

            security_groups = self._get_provider_security_groups_list(
                context, project_mapper)
            nics = self._get_provider_nics(context, project_mapper)

            provider_server = self.os_novaclient(context).create_server(
                name, image_ref, sub_flavor_id, meta=metadata,
                files=agent_inject_files,
                reservation_id=instance.reservation_id,
                security_groups=security_groups,
                nics=nics,
                availability_zone=project_mapper.get("availability_zone", None),
                block_device_mapping_v2=sub_bdm)

            LOG.debug('wait for server active')
            try:
                self.os_novaclient(context).check_create_server_complete(
                    provider_server)
            except Exception as ex:
                # rollback
                with excutils.save_and_reraise_exception():
                    provider_server.delete()
            LOG.debug('create server success.............!!!')

            try:
                # instance mapper
                values = {'provider_instance_id': provider_server.id}
                self.caa_db_api.instance_mapper_create(context,
                                                       instance.uuid,
                                                       instance.project_id,
                                                       values)
            except Exception as ex:
                LOG.exception(_LE("instance_mapper_create failed! ex = %s"), ex)
                provider_server.delete()
                raise

            interface_list = self.os_novaclient(context).interface_list(
                provider_server)
            ips = []
            for interface in interface_list:
                ip = interface.fixed_ips[0].get('ip_address')
                ips.append(ip)
            instance_ips = ','.join(ips)
            LOG.debug('luorui debug instance_ips %s' % instance_ips)
            instance.system_metadata['instance_ips'] = instance_ips
            instance.system_metadata['instance_id'] = provider_server.id
            try:
                instance.save()
            except Exception:
                pass
                # raise exception_ex.InstanceSaveFailed(
                #    instance_uuid=instance.uuid)
        except exception_ex.InstanceSaveFailed:
            raise
        except Exception as e:
            LOG.error(
                'Exception when spawn, exception: %s' % traceback.format_exc(e))
            raise Exception(
                'Exception when spawn, exception: %s' % traceback.format_exc(e))

    def spawn(self, context, instance, image_meta, injected_files,
              admin_password, network_info=None, block_device_info=None):
        """Create a new instance/VM/domain on the virtualization platform.

        Once this successfully completes, the instance should be
        running (power_state.RUNNING).

        If this fails, any partial instance should be completely
        cleaned up, and the virtualization platform should be in the state
        that it was before this call began.

        :param context: security context
        :param instance: nova.objects.instance.Instance
                         This function should use the data there to guide
                         the creation of the new instance.
                         Instance(
                             access_ip_v4=None,
                             access_ip_v6=None,
                             architecture=None,
                             auto_disk_config=False,
                             availability_zone='az31.shenzhen--aws',
                             cell_name=None,
                             cleaned=False,
                             config_drive='',
                             created_at=2015-08-31T02:44:36Z,
                             default_ephemeral_device=None,
                             default_swap_device=None,
                             deleted=False,
                             deleted_at=None,
                             disable_terminate=False,
                             display_description='server@daa5e17c-cb2c-4014-9726-b77109380ca6',
                             display_name='server@daa5e17c-cb2c-4014-9726-b77109380ca6',
                             ephemeral_gb=0,
                             ephemeral_key_uuid=None,
                             fault=<?>,
                             host='42085B38-683D-7455-A6A3-52F35DF929E3',
                             hostname='serverdaa5e17c-cb2c-4014-9726-b77109380ca6',
                             id=49,
                             image_ref='6004b47b-d453-4695-81be-cd127e23f59e',
                             info_cache=InstanceInfoCache,
                             instance_type_id=2,
                             kernel_id='',
                             key_data=None,
                             key_name=None,
                             launch_index=0,
                             launched_at=None,
                             launched_on='42085B38-683D-7455-A6A3-52F35DF929E3',
                             locked=False,
                             locked_by=None,
                             memory_mb=512,
                             metadata={},
                             node='h',
                             numa_topology=None,
                             os_type=None,
                             pci_devices=<?>,
                             power_state=0,
                             progress=0,
                             project_id='52957ad92b2146a0a2e2b3279cdc2c5a',
                             ramdisk_id='',
                             reservation_id='r-d1dkde4x',
                             root_device_name='/dev/sda',
                             root_gb=1,
                             scheduled_at=None,
                             security_groups=SecurityGroupList,
                             shutdown_terminate=False,
                             system_metadata={
                                 image_base_image_ref='6004b47b-d453-4695-81be-cd127e23f59e',
                                 image_container_format='bare',
                                 image_disk_format='qcow2',
                                 image_min_disk='1',
                                 image_min_ram='0',
                                 instance_type_ephemeral_gb='0',
                                 instance_type_flavorid='1',
                                 instance_type_id='2',
                                 instance_type_memory_mb='512',
                                 instance_type_name='m1.tiny',
                                 instance_type_root_gb='1',
                                 instance_type_rxtx_factor='1.0',
                                 instance_type_swap='0',
                                 instance_type_vcpu_weight=None,
                                 instance_type_vcpus='1'
                                 },
                             task_state='spawning',
                             terminated_at=None,
                             updated_at=2015-08-31T02:44:38Z,
                             user_data=u'<SANITIZED>,
                             user_id='ea4393b196684c8ba907129181290e8d',
                             uuid=92d22a62-c364-4169-9795-e5a34b5f5968,
                             vcpus=1,
                             vm_mode=None,
                             vm_state='building')
        :param image_meta: image object returned by nova.image.glance that
                           defines the image from which to boot this instance
                           e.g.
                           {
                               u'status': u'active',
                               u'deleted': False,
                               u'container_format': u'bare',
                               u'min_ram': 0,
                               u'updated_at': u'2015-08-17T07:46:48.708903',
                               u'min_disk': 0,
                               u'owner': u'52957ad92b2146a0a2e2b3279cdc2c5a',
                               u'is_public': True,
                               u'deleted_at': None,
                               u'properties': {},
                               u'size': 338735104,
                               u'name': u'emall-backend',
                               u'checksum': u'0f2294c98c7d113f0eb26ad3e76c86fa',
                               u'created_at': u'2015-08-17T07:46:20.581706',
                               u'disk_format': u'qcow2',
                               u'id': u'6004b47b-d453-4695-81be-cd127e23f59e'
                            }

        :param injected_files: User files to inject into instance.
        :param admin_password: Administrator password to set in instance.
        :param network_info:
           :py:meth:`~nova.network.manager.NetworkManager.get_instance_nw_info`
        :param block_device_info: Information about block devices to be
                                  attached to the instance.
        """

        # self._binding_host(context, network_info, instance.uuid)
        self._spawn(context, instance, image_meta, injected_files,
                    admin_password, network_info, block_device_info)
        # self._binding_host(context, network_info, instance.uuid)

    def pause(self, instance):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)
        provider_instance = self._get_provider_instance(context, instance)
        self.os_novaclient(context).pause(provider_instance)
        self.os_novaclient(context).check_pause_server_complete(
            provider_instance)

    def unpause(self, instance):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)
        provider_instance = self._get_provider_instance(context, instance)
        self.os_novaclient(context).unpause(provider_instance)
        self.os_novaclient(context).check_unpause_server_complete(
            provider_instance)

    def sub_flavor_detail(self, context):
        """get flavor detail"""

        ret = []
        sub_flavors = self.os_novaclient(context).get_flavor_detail()
        for sub_flavor in sub_flavors:
            ret.append(sub_flavor._info)

        return ret

    def rename(self, ctxt, instance, display_name=None):
        provider_uuid = self._get_provider_instance_id(ctxt, instance.uuid)
        if not display_name:
            display_name = instance.display_name

        provider_name = self._generate_provider_instance_name(display_name,
                                                              instance.uuid)
        self.os_novaclient(ctxt).rename(provider_uuid, provider_name)

    def get_diagnostics(self, instance):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)
        provider_uuid = self._get_provider_instance_id(context, instance.uuid)
        return self.os_novaclient(context).get_diagnostics(provider_uuid)

    def get_instance_diagnostics(self, instance):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)
        provider_uuid = self._get_provider_instance_id(context, instance.uuid)
        return self.os_novaclient(context).get_diagnostics(provider_uuid)

    def resume_state_on_host_boot(self, context, instance, network_info,
                                  block_device_info=None):
        """resume guest state when a host is booted."""
        # Check if the instance is running already and avoid doing
        # anything if it is.
        try:
            provider_instance = self._get_provider_instance(context, instance)

            ignored_states = ("ACTIVE",
                              "SUSPENDED",
                              "PAUSED")

            if provider_instance.status in ignored_states:
                return

            provider_instance.reboot('HARD')
        except exception.NovaException:
            pass

    def rescue(self, context, instance, network_info, image_meta,
               rescue_password):

        provider_instance = self._get_provider_instance(context, instance)

        rescue_image_id = None
        if image_meta.obj_attr_is_set("id"):
            rescue_image_id = image_meta.id

        image_id = (rescue_image_id or CONF.libvirt.rescue_image_id or
                    instance.image_ref)

        provider_image_id = self._get_provider_image_id(context, image_id)

        LOG.debug("+++image id = %s", provider_image_id)

        provider_instance.rescue(rescue_password, provider_image_id)

        self.os_novaclient(context).check_rescue_instance_complete(
            provider_instance)

    def unrescue(self, instance, network_info):

        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)

        provider_instance = self._get_provider_instance(context, instance)
        provider_instance.unrescue()

        self.os_novaclient(context).check_unrescue_instance_complete(
            provider_instance)

    def trigger_crash_dump(self, instance):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)

        provider_instance_uuid = self._get_provider_instance_id(context,
                                                                instance.uuid)
        return self.os_novaclient(context).trigger_crash_dump(
            provider_instance_uuid)

    def set_admin_password(self, instance, new_pass):
        context = req_context.RequestContext(is_admin=True,
                                             project_id=instance.project_id)

        provider_instance_uuid = self._get_provider_instance_id(context,
                                                                instance.uuid)
        self.os_novaclient(context).change_password(
            provider_instance_uuid, new_pass)

    def get_host_uptime(self):
        """Returns the result of calling "uptime"."""
        out, err = utils.execute('env', 'LANG=C', 'uptime')
        return out

    def attach_interface(self, instance, image_meta, vif):
        pass

    def detach_interface(self, instance, vif):
        pass

    def upload_image(self, context, instance, image_meta):

        LOG.debug("begin to upload image", instance=instance)

        image_id = image_meta['id']
        lxc_provider_volume_id = \
            instance.system_metadata.get('provider_lxc_volume_id', None)
        if not lxc_provider_volume_id:
            raise exception_ex.LxcVolumeNotFound(instance_uuid=instance.uuid)

        LOG.debug("lxc volume id = %s", lxc_provider_volume_id,
                  instance=instance)
        image = self._image_api.get(context, image_id)
        LOG.debug("+++hw, image = %s", image)
        provider_volume = self.os_cinderclient(context).get_volume(
            lxc_provider_volume_id)
        mountpoint = self._get_mountpoint_for_volume(provider_volume)

        # detach volume, can upload image
        # try:
        #     self._detach_volume(context, provider_volume)
        # except Exception as ex:
        #     LOG.exception(_LE("detach provider volume(%s) failed. ex = %s"),
        #                   lxc_provider_volume_id, ex)
        #     raise

        try:
            # provider create image
            provider_image = provider_volume.upload_to_image(
                True, image["name"],
                image_meta.get("container-format", "bare"),
                image_meta.get("disk_format", image.get('disk_format', 'raw')))
        except Exception as ex:
            LOG.exception(_LE("upload image failed! ex = %s"), ex)
            raise
            # with excutils.save_and_reraise_exception():
            #    self._attach_volume(context, instance, provider_volume,
            #                        mountpoint)
        provider_image = provider_image[1]["os-volume_upload_image"]

        try:
            # wait upload image success
            self.os_cinderclient(context).check_upload_image_volume_complete(
                provider_volume.id)

            # wait image status active
            self.os_glanceclient(context).check_image_active_complete(
                provider_image["image_id"])

            # update image property
            kwargs = {}
            image_properties = image.get("properties", {})
            if image_properties.get('__os_bit', None):
                kwargs['__os_bit'] = image_properties.get('__os_bit')
            if image_properties.get('__os_type', None):
                kwargs['__os_type'] = image_properties.get('__os_type')
            if image_properties.get('__os_version', None):
                kwargs['__os_version'] = image_properties.get('__os_version')
            if image_properties.get('__paltform', None):
                kwargs['__paltform'] = image_properties.get('__paltform')

            self.os_glanceclient(context).update(provider_image["image_id"],
                                                 remove_props=None, **kwargs)

            # create image mapper
            values = {"provider_image_id": provider_image["image_id"],
                      'provider_checksum': provider_image.get("checksum", None)}
            self.caa_db_api.image_mapper_create(context, image_id,
                                                context.project_id,
                                                values)

        except Exception as ex:
            LOG.exception(_LE("upload image failed! ex = %s"), ex)
            with excutils.save_and_reraise_exception():
                # self._attach_volume(context, instance, provider_volume,
                #                    mountpoint)
                self.os_glanceclient(context).delete(provider_image["image_id"])
