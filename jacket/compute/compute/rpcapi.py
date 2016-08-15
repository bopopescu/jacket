# Copyright 2013 Red Hat, Inc.
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
Client side of the compute RPC API.
"""

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_serialization import jsonutils

from jacket.compute import context
from jacket.compute import exception
from jacket.i18n import _, _LI, _LE
from jacket.objects import compute
from jacket.objects.compute import base as objects_base
from jacket.objects.compute import migrate_data as migrate_data_obj
from jacket.objects.compute import service as service_obj
from jacket import rpc

rpcapi_opts = [
    cfg.StrOpt('jacket_topic',
               default='jacket',
               help='The topic compute nodes listen on'),
]

CONF = cfg.CONF
CONF.register_opts(rpcapi_opts)

rpcapi_cap_opt = cfg.StrOpt('compute',
        help='Set a version cap for messages sent to compute services. '
             'Set this option to "auto" if you want to let the compute RPC '
             'module automatically determine what version to use based on '
             'the service versions in the deployment. '
             'Otherwise, you can set this to a specific version to pin this '
             'service to messages at a particular level. '
             'All services of a single type (i.e. compute) should be '
             'configured to use the same version, and it should be set '
             'to the minimum commonly-supported version of all those '
             'services in the deployment.')


CONF.register_opt(rpcapi_cap_opt, 'upgrade_levels')

LOG = logging.getLogger(__name__)
LAST_VERSION = None


def _compute_host(host, instance):
    '''Get the destination host for a message.

    :param host: explicit host to send the message to.
    :param instance: If an explicit host was not specified, use
                     instance['host']

    :returns: A host
    '''
    if host:
        return host
    if not instance:
        raise exception.NovaException(_('No compute host specified'))
    if not instance.host:
        raise exception.NovaException(_('Unable to find host for '
                                        'Instance %s') % instance.uuid)
    return instance.host


class JacketAPI(object):
    '''Client side of the jacket rpc API.
    '''

    def __init__(self):
        super(JacketAPI, self).__init__()
        target = messaging.Target(topic=CONF.compute_topic, version='1.0')
        version_cap = '1.0'
        serializer = objects_base.NovaObjectSerializer()
        self.client = self.get_client(target, version_cap, serializer)

    def _compat_ver(self, current, legacy):
        if self.client.can_send_version(current):
            return current
        else:
            return legacy

    # Cells overrides this
    def get_client(self, target, version_cap, serializer):
        return rpc.get_client(target,
                              version_cap=version_cap,
                              serializer=serializer)

    def add_aggregate_host(self, ctxt, aggregate, host_param, host,
                           slave_info=None):
        '''Add aggregate host.

        :param ctxt: request context
        :param aggregate:
        :param host_param: This value is placed in the message to be the 'host'
                           parameter for the remote method.
        :param host: This is the host to send the message to.
        '''
        self.client.cast(ctxt, 'add_aggregate_host',
                   aggregate=aggregate, host=host_param,
                   slave_info=slave_info)

    def add_fixed_ip_to_instance(self, ctxt, instance, network_id):
        self.client.cast(ctxt, 'add_fixed_ip_to_instance',
                   instance=instance, network_id=network_id)

    def attach_interface(self, ctxt, instance, network_id, port_id,
                         requested_ip):
        return self.client.call(ctxt, 'attach_interface',
                   instance=instance, network_id=network_id,
                   port_id=port_id, requested_ip=requested_ip)

    def attach_volume(self, ctxt, instance, bdm):
        self.client.cast(ctxt, 'attach_volume', instance=instance, bdm=bdm)

    def change_instance_metadata(self, ctxt, instance, diff):
        self.client.cast(ctxt, 'change_instance_metadata',
                   instance=instance, diff=diff)

    def check_can_live_migrate_destination(self, ctxt, instance, destination,
                                           block_migration, disk_over_commit):
        return self.client.call(ctxt, 'check_can_live_migrate_destination',
                                instance=instance,
                                block_migration=block_migration,
                                disk_over_commit=disk_over_commit)

    def check_can_live_migrate_source(self, ctxt, instance, dest_check_data):
        return self.client.call(ctxt, 'check_can_live_migrate_source',
                                instance=instance,
                                dest_check_data=dest_check_data)

    def check_instance_shared_storage(self, ctxt, instance, data, host=None):
        return self.client.call(ctxt, 'check_instance_shared_storage',
                                instance=instance,
                                data=data)

    def confirm_resize(self, ctxt, instance, migration, host,
            reservations=None, cast=True):
        cctxt = self.client
        rpc_method = cctxt.cast if cast else cctxt.call
        return rpc_method(ctxt, 'confirm_resize',
                          instance=instance, migration=migration,
                          reservations=reservations)

    def detach_interface(self, ctxt, instance, port_id):
        self.client.cast(ctxt, 'detach_interface',
                   instance=instance, port_id=port_id)

    def detach_volume(self, ctxt, instance, volume_id, attachment_id=None):
        self.client.cast(ctxt, 'detach_volume',
                   instance=instance, volume_id=volume_id, **extra)

    def finish_resize(self, ctxt, instance, migration, image, disk_info,
            host, reservations=None):
        self.client.cast(ctxt, 'finish_resize',
                   instance=instance, migration=migration,
                   image=image, disk_info=disk_info, reservations=reservations)

    def finish_revert_resize(self, ctxt, instance, migration, host,
                             reservations=None):
        self.client.cast(ctxt, 'finish_revert_resize',
                   instance=instance, migration=migration,
                   reservations=reservations)

    def get_console_output(self, ctxt, instance, tail_length):
        return self.client.call(ctxt, 'get_console_output',
                          instance=instance, tail_length=tail_length)

    def get_console_pool_info(self, ctxt, console_type, host):
        return self.client.call(ctxt, 'get_console_pool_info',
                          console_type=console_type)

    def get_console_topic(self, ctxt, host):
        return self.client.call(ctxt, 'get_console_topic')

    def get_diagnostics(self, ctxt, instance):
        return self.client.call(ctxt, 'get_diagnostics', instance=instance)

    def get_instance_diagnostics(self, ctxt, instance):
        # TODO(danms): This needs to be fixed for compute
        instance_p = jsonutils.to_primitive(instance)
        kwargs = {'instance': instance_p}
        return self.client.call(ctxt, 'get_instance_diagnostics', **kwargs)

    def get_vnc_console(self, ctxt, instance, console_type):
        return self.client.call(ctxt, 'get_vnc_console',
                          instance=instance, console_type=console_type)

    def get_spice_console(self, ctxt, instance, console_type):
        return self.client.call(ctxt, 'get_spice_console',
                          instance=instance, console_type=console_type)

    def get_rdp_console(self, ctxt, instance, console_type):
        return self.client.call(ctxt, 'get_rdp_console',
                          instance=instance, console_type=console_type)

    def get_mks_console(self, ctxt, instance, console_type):
        return self.client.call(ctxt, 'get_mks_console',
                          instance=instance, console_type=console_type)

    def get_serial_console(self, ctxt, instance, console_type):
        return self.client.call(ctxt, 'get_serial_console',
                          instance=instance, console_type=console_type)

    def validate_console_port(self, ctxt, instance, port, console_type):
        return self.client.call(ctxt, 'validate_console_port',
                          instance=instance, port=port,
                          console_type=console_type)

    def host_maintenance_mode(self, ctxt, host_param, mode, host):
        '''Set host maintenance mode

        :param ctxt: request context
        :param host_param: This value is placed in the message to be the 'host'
                           parameter for the remote method.
        :param mode:
        :param host: This is the host to send the message to.
        '''
        return self.client.call(ctxt, 'host_maintenance_mode',
                          host=host_param, mode=mode)

    def host_power_action(self, ctxt, action, host):
        return self.client.call(ctxt, 'host_power_action', action=action)

    def inject_network_info(self, ctxt, instance):
        self.client.cast(ctxt, 'inject_network_info', instance=instance)

    def live_migration(self, ctxt, instance, dest, block_migration, host,
                       migration, migrate_data=None):
        args = {'migration': migration}
        self.client.cast(ctxt, 'live_migration', instance=instance,
                   dest=dest, block_migration=block_migration,
                   migrate_data=migrate_data, **args)

    def live_migration_force_complete(self, ctxt, instance, migration_id):
        self.client.cast(ctxt, 'live_migration_force_complete', instance=instance,
                   migration_id=migration_id)

    def live_migration_abort(self, ctxt, instance, migration_id):
        self.client.cast(ctxt, 'live_migration_abort', instance=instance,
                migration_id=migration_id)

    def pause_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'pause_instance', instance=instance)

    def post_live_migration_at_destination(self, ctxt, instance,
            block_migration, host):
        self.client.cast(ctxt, 'post_live_migration_at_destination',
            instance=instance, block_migration=block_migration)

    def pre_live_migration(self, ctxt, instance, block_migration, disk,
            host, migrate_data=None):
        return self.client.call(ctxt, 'pre_live_migration',
                            instance=instance,
                            block_migration=block_migration,
                            disk=disk, migrate_data=migrate_data)

    def prep_resize(self, ctxt, image, instance, instance_type, host,
                    reservations=None, request_spec=None,
                    filter_properties=None, node=None,
                    clean_shutdown=True):
        image_p = jsonutils.to_primitive(image)
        msg_args = {'instance': instance,
                    'instance_type': instance_type,
                    'image': image_p,
                    'reservations': reservations,
                    'request_spec': request_spec,
                    'filter_properties': filter_properties,
                    'node': node,
                    'clean_shutdown': clean_shutdown}
        self.client.cast(ctxt, 'prep_resize', **msg_args)

    def reboot_instance(self, ctxt, instance, block_device_info,
                        reboot_type):
        self.client.cast(ctxt, 'reboot_instance',
                   instance=instance,
                   block_device_info=block_device_info,
                   reboot_type=reboot_type)

    def rebuild_instance(self, ctxt, instance, new_pass, injected_files,
            image_ref, orig_image_ref, orig_sys_metadata, bdms,
            recreate=False, on_shared_storage=False, host=None, node=None,
            preserve_ephemeral=False, migration=None, limits=None,
            kwargs=None):
        # NOTE(danms): kwargs is only here for cells compatibility, don't
        # actually send it to compute
        extra = {'preserve_ephemeral': preserve_ephemeral,
                 'migration': migration,
                 'scheduled_node': node,
                 'limits': limits}
        self.client.cast(ctxt, 'rebuild_instance',
                   instance=instance, new_pass=new_pass,
                   injected_files=injected_files, image_ref=image_ref,
                   orig_image_ref=orig_image_ref,
                   orig_sys_metadata=orig_sys_metadata, bdms=bdms,
                   recreate=recreate, on_shared_storage=on_shared_storage,
                   **extra)

    def remove_aggregate_host(self, ctxt, aggregate, host_param, host,
                              slave_info=None):
        '''Remove aggregate host.

        :param ctxt: request context
        :param aggregate:
        :param host_param: This value is placed in the message to be the 'host'
                           parameter for the remote method.
        :param host: This is the host to send the message to.
        '''
        self.client.cast(ctxt, 'remove_aggregate_host',
                   aggregate=aggregate, host=host_param,
                   slave_info=slave_info)

    def remove_fixed_ip_from_instance(self, ctxt, instance, address):
        self.client.cast(ctxt, 'remove_fixed_ip_from_instance',
                   instance=instance, address=address)

    def remove_volume_connection(self, ctxt, volume_id, instance, host):
        return self.client.call(ctxt, 'remove_volume_connection',
                          instance=instance, volume_id=volume_id)

    def rescue_instance(self, ctxt, instance, rescue_password,
                        rescue_image_ref=None, clean_shutdown=True):
        msg_args = {'rescue_password': rescue_password,
                    'clean_shutdown': clean_shutdown,
                    'rescue_image_ref': rescue_image_ref,
                    'instance': instance,
        }
        self.client.cast(ctxt, 'rescue_instance', **msg_args)

    def reset_network(self, ctxt, instance):
        self.client.cast(ctxt, 'reset_network', instance=instance)

    def resize_instance(self, ctxt, instance, migration, image, instance_type,
                        reservations=None, clean_shutdown=True):
        msg_args = {'instance': instance, 'migration': migration,
                    'image': image, 'reservations': reservations,
                    'instance_type': instance_type,
                    'clean_shutdown': clean_shutdown,
        }
        self.client.cast(ctxt, 'resize_instance', **msg_args)

    def resume_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'resume_instance', instance=instance)

    def revert_resize(self, ctxt, instance, migration, host,
                      reservations=None):
        self.client.cast(ctxt, 'revert_resize',
                   instance=instance, migration=migration,
                   reservations=reservations)

    def rollback_live_migration_at_destination(self, ctxt, instance, host,
                                               destroy_disks=True,
                                               migrate_data=None):
        self.client.cast(ctxt, 'rollback_live_migration_at_destination',
                   instance=instance, **extra)

    def set_admin_password(self, ctxt, instance, new_pass):
        return self.client.call(ctxt, 'set_admin_password',
                          instance=instance, new_pass=new_pass)

    def set_host_enabled(self, ctxt, enabled, host):
        return self.client.call(ctxt, 'set_host_enabled', enabled=enabled)

    def swap_volume(self, ctxt, instance, old_volume_id, new_volume_id):
        self.client.cast(ctxt, 'swap_volume',
                   instance=instance, old_volume_id=old_volume_id,
                   new_volume_id=new_volume_id)

    def get_host_uptime(self, ctxt, host):
        return self.client.call(ctxt, 'get_host_uptime')

    def reserve_block_device_name(self, ctxt, instance, device, volume_id,
                                  disk_bus=None, device_type=None):
        kw = {'instance': instance, 'device': device,
              'volume_id': volume_id, 'disk_bus': disk_bus,
              'device_type': device_type}

        return self.client.call(ctxt, 'reserve_block_device_name', **kw)

    def backup_instance(self, ctxt, instance, image_id, backup_type,
                        rotation):
        self.client.cast(ctxt, 'backup_instance',
                   instance=instance,
                   image_id=image_id,
                   backup_type=backup_type,
                   rotation=rotation)

    def snapshot_instance(self, ctxt, instance, image_id):
        self.client.cast(ctxt, 'snapshot_instance',
                   instance=instance,
                   image_id=image_id)

    def start_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'start_instance', instance=instance)

    def stop_instance(self, ctxt, instance, do_cast=True, clean_shutdown=True):
        msg_args = {'instance': instance,
                    'clean_shutdown': clean_shutdown}
        cctxt = self.client
        rpc_method = cctxt.cast if do_cast else cctxt.call
        return rpc_method(ctxt, 'stop_instance', **msg_args)

    def suspend_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'suspend_instance', instance=instance)

    def terminate_instance(self, ctxt, instance, bdms, reservations=None,
                           delete_type=None):
        # NOTE(rajesht): The `delete_type` parameter is passed because
        # the method signature has to match with `terminate_instance()`
        # method of cells rpcapi.
        self.client.cast(ctxt, 'terminate_instance',
                   instance=instance, bdms=bdms,
                   reservations=reservations)

    def unpause_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'unpause_instance', instance=instance)

    def unrescue_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'unrescue_instance', instance=instance)

    def soft_delete_instance(self, ctxt, instance, reservations=None):
        self.client.cast(ctxt, 'soft_delete_instance',
                   instance=instance, reservations=reservations)

    def restore_instance(self, ctxt, instance):
        self.client.cast(ctxt, 'restore_instance', instance=instance)

    def shelve_instance(self, ctxt, instance, image_id=None,
                        clean_shutdown=True):
        msg_args = {'instance': instance, 'image_id': image_id,
                    'clean_shutdown': clean_shutdown}
        self.client.cast(ctxt, 'shelve_instance', **msg_args)

    def shelve_offload_instance(self, ctxt, instance,
                                clean_shutdown=True):
        msg_args = {'instance': instance, 'clean_shutdown': clean_shutdown}
        self.client.cast(ctxt, 'shelve_offload_instance', **msg_args)

    def unshelve_instance(self, ctxt, instance, host, image=None,
                          filter_properties=None, node=None):
        msg_kwargs = {
            'instance': instance,
            'image': image,
            'filter_properties': filter_properties,
            'node': node,
        }
        self.client.cast(ctxt, 'unshelve_instance', **msg_kwargs)

    def volume_snapshot_create(self, ctxt, instance, volume_id,
                               create_info):
        self.client.cast(ctxt, 'volume_snapshot_create', instance=instance,
                   volume_id=volume_id, create_info=create_info)

    def volume_snapshot_delete(self, ctxt, instance, volume_id, snapshot_id,
                               delete_info):
        self.client.cast(ctxt, 'volume_snapshot_delete', instance=instance,
                   volume_id=volume_id, snapshot_id=snapshot_id,
                   delete_info=delete_info)

    def external_instance_event(self, ctxt, instances, events):
        self.client.cast(ctxt, 'external_instance_event', instances=instances,
                   events=events)

    def build_and_run_instance(self, ctxt, instance, host, image, request_spec,
            filter_properties, admin_password=None, injected_files=None,
            requested_networks=None, security_groups=None,
            block_device_mapping=None, node=None, limits=None):

        self.client.cast(ctxt, 'build_and_run_instance', instance=instance,
                image=image, request_spec=request_spec,
                filter_properties=filter_properties,
                admin_password=admin_password,
                injected_files=injected_files,
                requested_networks=requested_networks,
                security_groups=security_groups,
                block_device_mapping=block_device_mapping, node=node,
                limits=limits)

    def quiesce_instance(self, ctxt, instance):
        return self.client.call(ctxt, 'quiesce_instance', instance=instance)

    def unquiesce_instance(self, ctxt, instance, mapping=None):
        self.client.cast(ctxt, 'unquiesce_instance', instance=instance,
                   mapping=mapping)

    def refresh_instance_security_rules(self, ctxt, host, instance):
        self.client.cast(ctxt, 'refresh_instance_security_rules',
                   instance=instance)

    def trigger_crash_dump(self, ctxt, instance):
        return self.client.cast(ctxt, "trigger_crash_dump", instance=instance)
