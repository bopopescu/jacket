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

from jacket import conf
from jacket import context as req_context
from jacket import exception
from jacket.db.hybrid_cloud import api as hybrid_db_api
from jacket.db.storage import api as storage_db_api
from jacket.drivers.fs.clients import fs_context
from jacket.drivers.fs.clients import cinder as cinderclient
from jacket.drivers.fs.clients import glance as glanceclient
from jacket.storage.volume import driver

LOG = logging.getLogger(__name__)

CONF = conf.CONF


class FsVolumeDriver(driver.VolumeDriver):
    def __init__(self, *args, **kwargs):
        super(FsVolumeDriver, self).__init__(*args, **kwargs)

        self._fs_cinderclient = None
        self._fs_glanceclient = None
        self.storage_db = storage_db_api
        self.bybrid_db = hybrid_db_api
        self.PROVIDER_AVAILABILITY_ZONE = CONF.provider_opts.availability_zone

    def fs_cinderlient(self, context=None):
        if self._fs_cinderclient is None:
            fscontext = fs_context.FsClientContext(
                context, version='2', username=CONF.provider_opts.user,
                password=CONF.provider_opts.pwd,
                project_id=CONF.provider_opts.tenant,
                auth_url=CONF.provider_opts.auth_url,
                region_name=CONF.provider_opts.region
            )
            self._fs_cinderclient = cinderclient.CinderClientPlugin(fscontext)

        return self._fs_cinderclient

    def fs_glanceclient(self, context=None):
        if self._fs_glanceclient is None:
            fscontext = fs_context.FsClientContext(
                context, version='1', username=CONF.provider_opts.user,
                password=CONF.provider_opts.pwd,
                project_id=CONF.provider_opts.tenant,
                auth_url=CONF.provider_opts.auth_url,
                region_name=CONF.provider_opts.region
            )
            self._fs_glanceclient = glanceclient.GlanceClientPlugin(fscontext)

        return self._fs_glanceclient

    def check_for_setup_error(self):
        return

    def _get_sub_fs_volume_name(self, volume_name, volume_id):
        if not volume_name:
            volume_name = "volume"
        return '@'.join([volume_name, volume_id])

    def _get_sub_image_name(self, image_id):
        return '@'.join(['image', image_id])

    def copy_image_to_volume(self, context, volume, image_service, image_id):
        LOG.debug('dir volume: %s' % dir(volume))
        LOG.debug('volume: %s' % volume)

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_sub_fs_volume_name(
            volume.display_name, volume.id)

        try:
            exist_volume = self.fs_cinderlient(context).get_volume_by_name(
                volume_args['display_name'])
            if exist_volume:
                exist_volume.force_delete()
        except Exception:
            pass

        try:
            sub_image = self.fs_glanceclient(context).get_image(
                self._get_sub_image_name(image_id))
            if sub_image:
                image_ref = sub_image
                LOG.debug('sub image is: %s' % image_ref)
            else:
                image_id = CONF.provider_opts.base_linux_image
                image_ref = self.fs_glanceclient(context).get_image(image_id)
        except exception.NotFound:
            image_id = CONF.provider_opts.base_linux_image
            image_ref = self.fs_glanceclient(context).get_image(image_id)

        LOG.debug('image_ref: %s' % image_ref)

        volume_args['imageRef'] = image_ref.id

        volume_type_id = volume.volume_type_id
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            volume_type_obj = self.fs_cinderlient(
                context).get_volume_type_by_id(
                volume_type_id)
            LOG.debug('dir volume_type: %s, '
                      'volume_type: %s' % (volume_type_obj, volume_type_obj))
            volume_type_name = volume_type_obj.name
        else:
            volume_type_name = None

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        optionals = ('snapshot_id', 'source_volid',
                     'multiattach')

        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))
        sub_volume = self.fs_cinderlient(context).volume_create(**volume_args)
        LOG.debug('submit create-volume task to sub fs. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.fs_cinderlient(context).wait_for_volume_in_specified_status(
            sub_volume.id, 'available')

        LOG.debug('create volume %s success.' % volume.id)

    def copy_volume_to_image(self, context, volume, image_service, image_meta):
        pass

    def create_cloned_volume(self, volume, src_vref):
        """Create a clone of the specified volume."""
        pass

    def create_export(self, context, volume, connector):
        """Export the volume."""
        pass

    def create_snapshot(self, snapshot):
        pass

    def _get_typename(self, context, type_id):
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

    def create_volume(self, volume):
        LOG.debug('start to create volume')
        LOG.debug('volume glance image metadata: %s' %
                  volume.volume_glance_metadata)

        volume_args = {}
        volume_args['size'] = volume.size
        volume_args['display_description'] = volume.display_description
        volume_args['display_name'] = self._get_sub_fs_volume_name(
            volume.display_name, volume.id)

        # if volume.image_id:
        #    sub_image = self.fs_glanceclient().get_image(
        #        self._get_sub_image_name(volume.image_id))
        #    LOG.debug('sub_image: %s' % sub_image)
        #    if sub_image:
        #        volume_args['imageRef'] = sub_image.id
        #    else:
        #        volume_args['imageRef'] = CONF.provider_opts.base_linux_image

        volume_type_id = volume.volume_type_id
        LOG.debug('volume type id %s ' % volume_type_id)
        if volume_type_id:
            type_name = self._get_typename(req_context.get_admin_context(),
                                           volume_type_id)
            try:
                volume_type_obj = self.fs_cinderlient().get_volume_type(type_name)
                LOG.debug('dir volume_type: %s, '
                          'volume_type: %s' % (volume_type_obj, volume_type_obj))
                volume_type_name = volume_type_obj.name
            except exception.EntityNotFound:
                volume_type_name = CONF.provider_opts.volume_type
        else:
            volume_type_name = CONF.provider_opts.volume_type

        if volume_type_name:
            volume_args['volume_type'] = volume_type_name

        optionals = ('shareable', 'snapshot_id', 'source_volid',
                     'metadata', 'multiattach')

        volume_args.update((prop, getattr(volume, prop)) for prop in optionals
                           if getattr(volume, prop, None))

        sub_volume = self.fs_cinderlient().volume_create(**volume_args)
        LOG.debug('submit create-volume task to sub fs. '
                  'sub volume id: %s' % sub_volume.id)

        LOG.debug('start to wait for volume %s in status '
                  'available' % sub_volume.id)
        self.fs_cinderlient().wait_for_volume_in_specified_status(
            sub_volume.id, 'available')

        LOG.debug('create volume %s success.' % volume.id)

        LOG.debug('end to create volume')
        return {'provider_location': 'SUB-FusionSphere'}

    def create_volume_from_snapshot(self, volume, snapshot):
        """Create a volume from a snapshot."""
        pass

    def delete_snapshot(self, snapshot):
        """Delete a snapshot."""
        pass

    def delete_volume(self, volume):
        sub_volume_name = self._get_sub_fs_volume_name(volume.display_name,
                                                       volume.id)
        LOG.debug('sub_volume_name: %s' % sub_volume_name)

        sub_volume = self.fs_cinderlient().get_volume_by_name(sub_volume_name)
        if sub_volume:
            LOG.debug('submit delete-volume task')
            self.fs_cinderlient().volume_delete(sub_volume)
            LOG.debug('wait for volume delete')
            self.fs_cinderlient().wait_for_volume_deleted(sub_volume, 600)
        else:
            LOG.debug('no sub-volume exist, '
                      'no need to delete sub volume: %s' % sub_volume_name)

    def do_setup(self, context):
        """Instantiate common class and log in storage system."""
        pass

    def ensure_export(self, context, volume):
        """Synchronously recreate an export for a volume."""
        pass

    def extend_volume(self, volume, new_size):
        """Extend a volume."""
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

        driver_volume_type = 'fs_clouds_volume'
        data = {}
        data['backend'] = 'fsclouds'
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
        pass

    def detach_volume(self, context, volume):
        """Callback for volume detached."""
        pass
