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

    (Beginning of) the contract that volume drivers must follow, and shared
    types that support that contract
"""

from oslo_log import log as logging
from oslo_utils import excutils
import six

from jacket import conf
from jacket import context as req_context
from jacket import exception
from jacket.db.extend import api as caa_db_api
from jacket.db.storage import api as storage_db_api
from jacket.drivers.openstack.clients import os_context
from jacket.drivers.openstack.clients import cinder as cinderclient
from jacket.drivers.openstack.clients import glance as glanceclient
from jacket.drivers.openstack import exception_ex
from jacket.i18n import _LE, _LI
from jacket.storage.volume import driver

LOG = logging.getLogger(__name__)

CONF = conf.CONF


class OsVolumeDriver(driver.VolumeDriver):
    CLOUD_DRIVER = True

    def __init__(self, *args, **kwargs):
        super(OsVolumeDriver, self).__init__(*args, **kwargs)

        self._os_cinderclient = None
        self._os_glanceclient = None
        self.storage_db = storage_db_api
        self.caa_db = caa_db_api

    def os_cinderclient(self, context=None):
        if self._os_cinderclient is None:
            oscontext = os_context.OsClientContext(
                context, version='2')
            self._os_cinderclient = cinderclient.CinderClientPlugin(oscontext)

        return self._os_cinderclient

    def os_glanceclient(self, context=None):
        if self._os_glanceclient is None:
            oscontext = os_context.OsClientContext(
                context, version='2')
            self._os_glanceclient = glanceclient.GlanceClientPlugin(oscontext)

        return self._os_glanceclient

    def check_for_setup_error(self):
        return

    def _get_provider_volume_name(self, volume_name, volume_id):
        if not volume_name:
            volume_name = "volume"
        return '@'.join([volume_name, volume_id])

    def _get_provider_volume_id(self, context, caa_volume_id):
        volume_mapper = self.caa_db.volume_mapper_get(context, caa_volume_id)
        provider_volume_id = volume_mapper.get('provider_volume_id', None)
        if provider_volume_id:
            return provider_volume_id

        provider_volume = self.os_cinderclient(
            context).get_volume_by_caa_volume_id(
            caa_volume_id)
        if provider_volume is None:
            raise exception.EntityNotFound(entity='Volume',
                                           name=caa_volume_id)

        return provider_volume.id

    def _get_provider_volume(self, context, hybrid_volume):
        if isinstance(hybrid_volume, six.string_types):
            volume_id = hybrid_volume
        else:
            volume_id = hybrid_volume.id
        provider_volume_id = self._get_provider_volume_id(context,
                                                          volume_id)
        if provider_volume_id:
            return self.os_cinderclient(context).get_volume(provider_volume_id)

        sub_volume = self.os_cinderclient(context).get_volume_by_caa_volume_id(
            volume_id)
        if sub_volume is None:
            raise exception.EntityNotFound(entity='Volume',
                                           name=volume_id)

        return sub_volume

    def _get_project_mapper(self, context, project_id=None):
        if project_id is None:
            project_id = 'default'

        project_mapper = self.caa_db.project_mapper_get(context, project_id)
        if not project_mapper:
            project_mapper = self.caa_db.project_mapper_get(context,
                                                            'default')

        if not project_mapper:
            raise exception_ex.AccountNotConfig()

        return project_mapper

    def _get_sub_image_id(self, context, image_id):

        project_mapper = self._get_project_mapper(context, context.project_id)
        base_linux_image = project_mapper.get("base_linux_image", None)

        image_mapper = self.caa_db.image_mapper_get(context, image_id)
        sub_image_id = image_mapper.get("dest_image_id", base_linux_image)

        return sub_image_id

    def _get_type_name(self, context, type_id):
        found = False
        typename = None
        volume_type_list = self.storage_db.volume_type_get_all(context)
        for vt in volume_type_list.values():
            if type_id == vt.get('id'):
                found = True
                typename = vt.get('name')
                break

        if not found:
            raise exception.EntityNotFound(entity='VolumeType',
                                           name=type_id)

        return typename

    def _get_sub_type_name(self, context, type_id):
        type_name = self._get_type_name(context, type_id)
        try:
            volume_type_obj = self.os_cinderclient(context).get_volume_type(
                type_name)
            LOG.debug('dir volume_type: %s, '
                      'volume_type: %s' % (
                          volume_type_obj, volume_type_obj))
            volume_type_name = volume_type_obj.name
        except exception.EntityNotFound:
            project_mapper = self._get_project_mapper(context,
                                                      context.project_id)
            volume_type_name = project_mapper.get('volume_type', None)

        return volume_type_name

    def _get_sub_snapshot_name(self, snap_id, snap_name=None):
        if not snap_name:
            snap_name = 'snapshot'
        return "@".join([snap_name, snap_id])

    def _get_provider_snapshot_id(self, context, caa_snapshot_id):
        snapshot_mapper = self.caa_db.volume_snapshot_mapper_get(context,
                                                                 caa_snapshot_id)
        provider_snapshot_id = snapshot_mapper.get('provider_snapshot_id', None)
        if provider_snapshot_id:
            return provider_snapshot_id

        provider_snap = self.os_cinderclient(
            context).get_snapshot_by_caa_snap_id(
            caa_snapshot_id)
        if provider_snap is None:
            raise exception.EntityNotFound(entity='VolumeSnapshot',
                                           name=provider_snap)

        return provider_snap.id

    def _get_sub_snapshot(self, context, hybrid_snap):

        provider_snapshot_id = self._get_provider_snapshot_id(context,
                                                              hybrid_snap.id)
        if provider_snapshot_id:
            return self.os_cinderclient(context).get_volume_snapshot(
                provider_snapshot_id)

        sub_snap = self.os_cinderclient(context).get_snapshot_by_caa_snap_id(
            hybrid_snap.id)
        if sub_snap is None:
            raise exception.EntityNotFound(entity='VolumeSnapshot',
                                           name=hybrid_snap.id)

        return sub_snap

    def _get_provider_instance_id(self, context, caa_instance_id):
        instance_mapper = self.caa_db.instance_mapper_get(context,
                                                          caa_instance_id)
        return instance_mapper.get('provider_instance_id', None)

    def _get_attachment_id_for_volume(self, sub_volume):
        LOG.debug('start to _get_attachment_id_for_volume: %s' % sub_volume)
        attachment_id = None
        server_id = None
        attachments = sub_volume.attachments
        LOG.debug('attachments: %s' % attachments)
        for attachment in attachments:
            volume_id = attachment.get('volume_id')
            tmp_attachment_id = attachment.get('attachment_id')
            tmp_server_id = attachment.get('server_id')
            if volume_id == sub_volume.id:
                attachment_id = tmp_attachment_id
                server_id = tmp_server_id
                break
            else:
                continue

        return attachment_id, server_id

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        LOG.debug('dir volume: %s' % dir(volume))
        LOG.debug('volume: %s' % volume)

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_provider_volume_name(
            volume.display_name, volume.id)

        try:
            sub_image = self.os_glanceclient(context).get_image(
                self._get_sub_image_id(context, image_id))
        except Exception as ex:
            LOG.exception(_LE("get image(%(image_id)s) failed, "
                              "ex = %(ex)s"), image_id=image_id,
                          ex=ex)
            raise

        LOG.debug('image_ref: %s' % sub_image)
        volume_args['imageRef'] = sub_image.id

        volume_type_name = None
        volume_type_id = volume.volume_type_id
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            volume_type_name = self._get_sub_type_name(
                req_context.get_admin_context(), volume_type_id)

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        optionals = ('metadata', 'multiattach')
        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))

        if 'metadata' not in volume_args:
            volume_args['metadata'] = {}
        volume_args['metadata']['tag:caa_volume_id'] = volume.id

        sub_volume = self.os_cinderclient(context).create_volume(**volume_args)
        LOG.debug('submit create-volume task to sub os. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.os_cinderclient(context).check_create_volume_complete(
            sub_volume)

        try:
            # create volume mapper
            values = {"provider_volume_id": sub_volume.id}
            self.caa_db.volume_mapper_create(context, volume.id,
                                             context.project_id, values)
        except Exception as ex:
            LOG.exception(_LE("volume_mapper_create failed! ex = %s"), ex)
            sub_volume.delete()
            raise

        LOG.debug('create volume %s success.' % volume.id)

    def copy_volume_to_image(self, context, volume, image_service, image_meta):
        image_id = image_meta['id']
        LOG.debug("volume(%s), begin to copy_volume_to_image", volume.id)

        image = image_service.show(context, image_id)
        provider_volume = self._get_provider_volume(context, volume)

        # provider create image
        provider_image = provider_volume.upload_to_image(
            True, image["name"],
            image_meta.get("container-format", "bare"),
            image_meta.get("disk_format", "raw"))

        provider_image = provider_image[1]["os-volume_upload_image"]

        try:

            # wait upload image success
            self.os_cinderclient(context).check_upload_image_volume_complete(
                provider_volume.id)

            # wait image status active
            self.os_glanceclient(context).check_image_active_complete(
                provider_image["image_id"])

            # download from provider glance
            LOG.debug("+++hw, begin to download image(%s)",
                      provider_image["image_id"])
            image_data = self.os_glanceclient(context).data(
                provider_image["image_id"])
            LOG.debug("+++hw, image length = %s", len(image_data))
            image_service.update(context, image_id, {}, image_data)

            # create image mapper
            values = {"provider_image_id": provider_image["image_id"]}
            self.caa_db.image_mapper_create(context, image_id,
                                            context.project_id,
                                            values)

        except Exception as ex:
            LOG.exception(_LE("upload image failed! ex = %s"), ex)
            with excutils.save_and_reraise_exception():
                self.os_glanceclient(context).delete(provider_image["image_id"])

    def create_cloned_volume(self, volume, src_vref):
        """Create a clone of the specified volume."""
        LOG.debug('start to create volume from volume')

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_provider_volume_name(
            volume.display_name, volume.id)

        context = req_context.RequestContext(project_id=volume.project_id)
        volume_type_id = volume.volume_type_id
        volume_type_name = None
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            volume_type_name = self._get_sub_type_name(
                req_context.get_admin_context(), volume_type_id)

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        try:
            src_sub_volume = self._get_provider_volume(context, src_vref)
        except exception.EntityNotFound:
            LOG.exception(_LE("not found sub volume of %s"), src_vref.id)
            raise exception_ex.VolumeNotFoundAtProvider(
                volume_id=src_vref.id)

        volume_args['source_volid'] = src_sub_volume.id

        optionals = ('shareable', 'metadata', 'multiattach')
        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))

        if 'metadata' not in volume_args:
            volume_args['metadata'] = {}
        volume_args['metadata']['tag:caa_volume_id'] = volume.id

        sub_volume = self.os_cinderclient(context).create_volume(**volume_args)
        LOG.debug('submit create-volume task to sub os. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.os_cinderclient(context).check_create_volume_complete(
            sub_volume)

        try:
            # create volume mapper
            values = {"provider_volume_id": sub_volume.id}
            self.caa_db.volume_mapper_create(context, volume.id,
                                             context.project_id, values)
        except Exception as ex:
            LOG.exception(_LE("volume_mapper_create failed! ex = %s"), ex)
            sub_volume.delete()
            raise

        LOG.debug('create volume %s success.' % volume.id)

        return {'provider_location': 'SUB-FusionSphere'}

    def create_export(self, context, volume, connector):
        """Export the volume."""
        pass

    def create_volume(self, volume):
        LOG.debug('start to create volume')
        LOG.debug('volume glance image metadata: %s' %
                  volume.volume_glance_metadata)

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_provider_volume_name(
            volume.display_name, volume.id)

        context = req_context.RequestContext(project_id=volume.project_id)
        volume_type_id = volume.volume_type_id
        volume_type_name = None
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            volume_type_name = self._get_sub_type_name(
                req_context.get_admin_context(), volume_type_id)

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        optionals = ('shareable', 'metadata', 'multiattach')
        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))

        if 'metadata' not in volume_args:
            volume_args['metadata'] = {}
        volume_args['metadata']['tag:caa_volume_id'] = volume.id

        sub_volume = self.os_cinderclient(context).create_volume(**volume_args)
        LOG.debug('submit create-volume task to sub os. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.os_cinderclient(context).check_create_volume_complete(
            sub_volume)

        try:
            # create volume mapper
            values = {"provider_volume_id": sub_volume.id}
            self.caa_db.volume_mapper_create(context, volume.id,
                                             context.project_id, values)
        except Exception as ex:
            LOG.exception(_LE("volume_mapper_create failed! ex = %s"), ex)
            sub_volume.delete()
            raise

        LOG.debug('create volume %s success.' % volume.id)

        return {'provider_location': 'SUB-FusionSphere'}

    def delete_volume(self, volume):
        context = req_context.RequestContext(project_id=volume.project_id)
        try:
            sub_volume = self._get_provider_volume(context, volume)
        except exception.EntityNotFound:
            LOG.debug('no sub-volume exist, '
                      'no need to delete sub volume')
            return

        LOG.debug('submit delete-volume task')
        sub_volume.delete()
        LOG.debug('wait for volume delete')
        self.os_cinderclient(context).check_delete_volume_complete(
            sub_volume)

        try:
            # delelte volume snapshot mapper
            self.caa_db.volume_mapper_delete(context, volume.id,
                                             context.project_id)
        except Exception as ex:
            LOG.error(_LE("volume_mapper_delete failed! ex = %s"), ex)

    def extend_volume(self, volume, new_size):
        """Extend a volume."""

        context = req_context.RequestContext(project_id=volume.project_id)

        try:
            sub_volume = self._get_provider_volume(context, volume)
        except exception.EntityNotFound:
            LOG.exception(_LE("volume(%s) not found in provider cloud!"),
                          volume.id)
            raise exception_ex.VolumeNotFoundAtProvider(volume_id=volume.id)

        sub_volume.extend(sub_volume, new_size)
        self.os_cinderclient(context).check_extend_volume_complete(sub_volume)

        LOG.info(_LI("extend volume(%s) success!"), sub_volume.id)

    def create_volume_from_snapshot(self, volume, snapshot):
        """Create a volume from a snapshot."""
        LOG.debug('start to create volume from snapshot')

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_provider_volume_name(
            volume.display_name, volume.id)

        context = req_context.RequestContext(project_id=volume.project_id)
        volume_type_id = volume.volume_type_id
        volume_type_name = None
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            volume_type_name = self._get_sub_type_name(
                req_context.get_admin_context(), volume_type_id)

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        try:
            sub_snap = self._get_sub_snapshot(context, snapshot)
        except exception.EntityNotFound:
            LOG.exception(_LE("not found sub snapshot of %s"), snapshot.id)
            raise exception_ex.VolumeSnapshotNotFoundAtProvider(
                snapshot_id=snapshot.id)

        volume_args['snapshot_id'] = sub_snap.id

        optionals = ('shareable', 'metadata', 'multiattach')
        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))

        if 'metadata' not in volume_args:
            volume_args['metadata'] = {}
        volume_args['metadata']['tag:caa_volume_id'] = volume.id

        sub_volume = self.os_cinderclient(context).create_volume(**volume_args)
        LOG.debug('submit create-volume task to sub os. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.os_cinderclient(context).check_create_volume_complete(
            sub_volume)

        try:
            # create volume mapper
            values = {"provider_volume_id": sub_volume.id}
            self.caa_db.volume_mapper_create(context, volume.id,
                                             context.project_id, values)
        except Exception as ex:
            LOG.exception(_LE("volume_mapper_create failed! ex = %s"), ex)
            sub_volume.delete()
            raise

        LOG.debug('create volume %s success.' % volume.id)

        return {'provider_location': 'SUB-FusionSphere'}

    def create_snapshot(self, snapshot):
        volume_id = snapshot.volume.id
        volume_name = snapshot.volume.display_name
        context = snapshot.context

        try:
            sub_volume = self._get_provider_volume(context, snapshot.volume)
        except exception.EntityNotFound:
            LOG.exception(_LE("volume(%s) not found in provider cloud!"),
                          volume_id)
            raise exception_ex.VolumeNotFoundAtProvider(volume_id=volume_id)

        sub_sn_name = self._get_sub_snapshot_name(snapshot.id,
                                                  snapshot.display_name)

        metadata = snapshot.metadata
        if not metadata:
            metadata = {}

        metadata['tag:caa_snapshot_id'] = snapshot.id

        sub_snapshot = self.os_cinderclient(context).create_snapshot(
            sub_volume.id, force=True, name=sub_sn_name,
            description=snapshot.display_description,
            metadata=metadata)

        self.os_cinderclient(context).check_create_snapshot_complete(
            sub_snapshot.id)

        try:
            # create volume snapshot mapper
            values = {"provider_snapshot_id": sub_snapshot.id}
            self.caa_db.volume_snapshot_mapper_create(context, snapshot.id,
                                                      context.project_id,
                                                      values)
        except Exception as ex:
            LOG.exception(_LE("volume_snapshot_mapper_create failed! ex = %s"),
                          ex)
            sub_snapshot.delete()
            raise

        LOG.info(_LI("create snapshot(%(id)s) success!"), sub_snapshot.id)

    def delete_snapshot(self, snapshot):
        """Delete a snapshot."""
        context = snapshot.context

        try:
            sub_snap = self._get_sub_snapshot(context, snapshot)
        except exception.EntityNotFound:
            LOG.debug("sub snapshot is not exist, "
                      "no need to delete")
            return

        sub_snap.delete()
        self.os_cinderclient(context).check_delete_snapshot_complete(
            sub_snap.id)

        try:
            # delelte volume snapshot mapper
            self.caa_db.volume_snapshot_mapper_delete(context, snapshot.id,
                                                      context.project_id)
        except Exception as ex:
            LOG.error(_LE("volume_snapshot_mapper_delete failed! ex = %s"), ex)

        LOG.info(_LI("delete snapshot(%s) success!"), sub_snap.id)

    def do_setup(self, context):
        """Instantiate common class and log in storage system."""
        pass

    def ensure_export(self, context, volume):
        """Synchronously recreate an export for a volume."""
        pass

    def get_volume_stats(self, refresh=False):
        """Get volume stats."""
        # pdb.set_trace()
        if not self._stats:
            backend_name = self.configuration.safe_get('volume_backend_name')
            LOG.debug('*******backend_name is %s' % backend_name)
            if not backend_name:
                backend_name = 'FS'
            data = {'volume_backend_name': backend_name,
                    'vendor_name': 'Huawei',
                    'driver_version': self.VERSION,
                    'storage_protocol': 'LSI Logic SCSI',
                    'reserved_percentage': 0,
                    'total_capacity_gb': 1000,
                    'free_capacity_gb': 1000}
            self._stats = data
        return self._stats

    def initialize_connection(self, volume, connector):
        """Allow connection to connector and return connection info."""
        LOG.debug('vCloud Driver: initialize_connection')

        driver_volume_type = 'os_clouds_volume'
        data = {}
        data['backend'] = 'osclouds'
        data['volume_id'] = volume['id']
        data['display_name'] = volume['display_name']

        return {'driver_volume_type': driver_volume_type,
                'data': data}

    def remove_export(self, context, volume):
        """Remove an export for a volume."""
        pass

    def terminate_connection(self, volume, connector, **kwargs):
        """Disallow connection from connector"""
        LOG.debug('vCloud Driver: terminate_connection')
        pass

    def validate_connector(self, connector):
        """Fail if connector doesn't contain all the data needed by driver."""
        LOG.debug('vCloud Driver: validate_connector')
        pass

    def attach_volume(self, context, volume, instance_uuid, host_name,
                      mountpoint):
        """Callback for volume attached to instance or host."""
        LOG.debug('start to attach volume.')

        provider_instance_id = self._get_provider_instance_id(context,
                                                              instance_uuid)

        if provider_instance_id is None:
            # NOTE(instance may be not created)
            return

        cascading_volume_id = volume.id
        cascading_volume_name = volume.display_name
        su_volume_name = self._get_provider_volume_name(cascading_volume_name,
                                                        cascading_volume_id)

        LOG.debug("+++hw, su_volume_name = %s", su_volume_name)

        provider_volume = self._get_provider_volume(context, volume)
        if provider_volume.status == "in-use":
            attach_id, server_id = self._get_attachment_id_for_volume(
                provider_volume)
            if server_id != provider_instance_id:
                LOG.error(_LE("provider volume(%s) has been attached to "
                              "provider instance(%s)"), provider_volume.id,
                          server_id)
                raise exception_ex.VolumeAttachFailed(volume_id=volume.id)
            else:
                return

        if provider_volume.status == 'available':
            provider_volume.attach(provider_instance_id, mountpoint,
                                   host_name=host_name)

            self.os_cinderclient(context).check_attach_volume_complete(
                provider_volume)
        else:
            raise Exception('sub volume %s of volume: %s is not available, '
                            'status is %s' %
                            (provider_volume.id, cascading_volume_id,
                             provider_volume.status))
        LOG.debug('attach volume : %s success.' % cascading_volume_id)

    def detach_volume(self, context, volume, mountpoint):
        """Callback for volume detached."""
        try:
            provider_volume = self._get_provider_volume(context, volume)
            if provider_volume.status == "available":
                LOG.debug("provider volume(%s) has been detach",
                          provider_volume.id)
                return
        except exception_ex.EntityNotFound:
            return

        provider_volume.detach()

        self.os_cinderclient(context).check_detach_volume_complete(
            provider_volume)
        LOG.debug('detach volume : %s success.' % volume.id)

    def sub_vol_type_detail(self, context):
        """get volume type detail"""

        ret = []
        sub_vol_types = self.os_cinderclient(context).get_volume_type_detail()
        for sub_vol_type in sub_vol_types:
            ret.append(sub_vol_type._info)

        return ret

    def rename_volume(self, ctxt, volume, display_name=None):
        provider_uuid = self._get_provider_volume_id(ctxt, volume.id)

        if not display_name:
            display_name = volume.display_name

        provider_name = self._get_provider_volume_name(display_name,
                                                       volume.id)
        self.os_cinderclient(ctxt).update_volume(provider_uuid,
                                                 display_name=provider_name)

    def rename_snapshot(self, ctxt, snapshot, display_name=None):
        provider_uuid = self._get_provider_snapshot_id(ctxt, snapshot.id)
        if not display_name:
            display_name = snapshot.display_name

        provider_name = self._get_sub_snapshot_name(snapshot.id, display_name)
        self.os_cinderclient(ctxt).update_snapshot(provider_uuid,
                                                   display_name=provider_name)
