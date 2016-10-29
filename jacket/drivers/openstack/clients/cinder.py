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

import functools

from cinderclient import client as cc
from cinderclient import exceptions
from oslo_log import log as logging
from oslo_utils import excutils
from retrying import retry
import six

from jacket import conf
from jacket.drivers.openstack import exception_ex
from jacket.drivers.openstack.clients import client_plugin
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LI

LOG = logging.getLogger(__name__)

CONF = conf.CONF
CLIENT_RETRY_LIMIT = CONF.clients_drivers.client_retry_limit


def wrap_auth_failed(function):

    @functools.wraps(function)
    def decorated_function(self, *args, **kwargs):
        try:
            return function(self, *args, **kwargs)
        except (exceptions.Unauthorized):
            with excutils.save_and_reraise_exception():
                self.os_context.auth_refresh()
                self.invalidate()
                raise exception_ex.Unauthorized()
    return decorated_function


class CinderClientPlugin(client_plugin.ClientPlugin):
    exceptions_module = exceptions
    CLIENT_NAME = 'cinder'
    SUPPORTED_VERSION = [V2, V3] = ['2', '3']
    DEFAULT_API_VERSION = V2
    DEFAULT_CATALOG_INFO = {
        V2: {"service_type": "volumev2",
             "service_name": "cinderv2",
             "interface": "publicURL"},
        V3: {"service_type": "volumev3",
             "service_name": "cinderv3",
             "interface": "publicURL"},
    }

    def _create(self, version=None):
        version = self.os_context.version
        extensions = cc.discover_extensions(version)

        args = self.os_context.to_dict()
        args.update(
            {
                'extensions': extensions,
                'http_log_debug': self._get_client_option(self.CLIENT_NAME,
                                                          'http_log_debug')
            }
        )

        args.pop('version')
        args['api_key'] = args.pop("password")

        client = cc.Client(version, **args)
        return client

    def _list_extensions(self):
        extensions = self.client().list_extensions.show_all()
        return set(extension.alias for extension in extensions)

    def has_extension(self, alias):
        """Check if specific extension is present."""
        return alias in self._list_extensions()

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume(self, volume):
        try:
            return self.client().volumes.get(volume)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Volume', name=volume)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_by_name(self, volume_name):
        volume_list = self.client().volumes.list(
            search_opts={'name': volume_name})
        if volume_list and len(volume_list) > 0:
            return volume_list[0]
        else:
            return None

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_by_caa_volume_id(self, caa_volume_id):
        volume_list = self.client().volumes.list()
        if volume_list is None or len(volume_list) <= 0:
            return None

        for volume in volume_list:
            if hasattr(volume, 'metadata'):
                temp_id = volume.metadata.get('tag:caa_volume_id', None)
                if temp_id == caa_volume_id:
                    return volume
        return None

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_type(self, volume_type):
        vt_id = None
        volume_type_list = self.client().volume_types.list()
        for vt in volume_type_list:
            if volume_type in [vt.name, vt.id]:
                vt_id = vt.id
                break
        if vt_id is None:
            raise exception.EntityNotFound(entity='VolumeType',
                                           name=volume_type)

        return vt_id

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_type_by_id(self, volume_type_id):
        volume_type = self.client().volume_types.get(volume_type_id)
        return volume_type

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_type_detail(self):
        volume_types = self.client().volume_types.list()
        return volume_types

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_qos_specs(self, qos_specs):
        try:
            qos = self.client().qos_specs.get(qos_specs)
        except exceptions.NotFound:
            qos = self.client().qos_specs.find(name=qos_specs)
        return qos.id

    def is_not_found(self, ex):
        return isinstance(ex, exceptions.NotFound)

    def is_over_limit(self, ex):
        return isinstance(ex, exceptions.OverLimit)

    def is_conflict(self, ex):
        return (isinstance(ex, exceptions.ClientException) and
                ex.code == 409)

    def check_opt_volume_complete(self, opt, volume,
                                  by_status=[],
                                  expect_status=[],
                                  not_expect_status=[],
                                  is_ignore_not_found=False):
        try:
            if isinstance(volume, six.string_types):
                volume = self.client().volumes.get(volume)
            else:
                volume.get()
        except Exception as ex:
            if not is_ignore_not_found and not self.ignore_not_found(ex):
                raise
            return True

        if volume.status in by_status:
            LOG.debug('volume(%s) status(%s) not expect status, continue',
                      volume.id, volume.status)
            return False

        LOG.debug('Volume %(id)s - status: %(status)s' % {
            'id': volume.id, 'status': volume.status})

        if not_expect_status and volume.status in not_expect_status:
            LOG.debug("%(opt)s failed - volume %(vol)s "
                      "is in %(status)s status" % {"opt": opt,
                                                   "vol": volume.id,
                                                   "status": volume.status})
            raise exception.ResourceUnknownStatus(
                resource_status=volume.status,
                result=_('Volume %s failed') % opt)

        if expect_status and volume.status not in expect_status:
            LOG.debug("%(opt)s failed - volume %(vol)s "
                      "is in %(status)s status" % {"opt": opt,
                                                   "vol": volume.id,
                                                   "status": volume.status})
            raise exception.ResourceUnknownStatus(
                resource_status=volume.status,
                result=_('Volume %s failed') % opt)
        else:
            LOG.info(_LI('%(opt)s volume %(id)s complete'), {'opt': opt,
                                                             'id': volume.id})
            return True

    @retry(stop_max_attempt_number=60,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_detach_volume_complete(self, volume):

        LOG.info(_LI("wait volume(%s) detach complete"), volume)
        by_status = ['in-use', 'detaching']
        expect_status = ['available', 'deleting']
        return self.check_opt_volume_complete("detach", volume, by_status,
                                              expect_status)

    @retry(stop_max_attempt_number=60,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_attach_volume_complete(self, volume):

        LOG.info(_LI("wait volume(%s) attach complete"), volume)
        by_status = ['available', 'attaching']
        expect_status = ['in-use']
        return self.check_opt_volume_complete("attach", volume, by_status,
                                              expect_status)

    @retry(stop_max_attempt_number=900,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_create_volume_complete(self, volume):
        LOG.info(_LI("wait volume(%s) create complete"), volume)
        by_status = ['creating', 'downloading']
        expect_status = ['available']
        return self.check_opt_volume_complete("create", volume, by_status,
                                              expect_status)

    @retry(stop_max_attempt_number=900,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_delete_volume_complete(self, volume):
        LOG.info(_LI("wait volume(%s) delete complete"), volume)
        by_status = ['deleting']
        expect_status = []
        not_expect_status = ['error']
        return self.check_opt_volume_complete("create", volume, by_status,
                                              expect_status,
                                              not_expect_status,
                                              is_ignore_not_found=True)

    @retry(stop_max_attempt_number=60,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_extend_volume_complete(self, volume):
        LOG.info(_LI("wait volume(%s) extend complete"), volume)
        by_status = ['extending']
        expect_status = ['available']
        not_expect_status = ['error_extending']
        return self.check_opt_volume_complete("extend", volume, by_status,
                                              expect_status,
                                              not_expect_status)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def create_volume(self, size=None, snapshot_id=None, source_volid=None,
                      display_name=None, display_description=None,
                      volume_type=None, user_id=None,
                      project_id=None, availability_zone=None,
                      metadata=None, imageRef=None, shareable=False):
        return self.client().volumes.create(
            size, snapshot_id=snapshot_id,
            source_volid=source_volid, name=display_name,
            description=display_description,
            volume_type=volume_type, user_id=user_id,
            project_id=project_id, availability_zone=availability_zone,
            metadata=metadata, imageRef=imageRef)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def delete_volume(self, volume):
        """Delete a volume.

        :param volume: The :class:`Volume` to delete.
        """
        return self.client().volumes.delete(volume)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def update_volume(self, volume_id, **kwargs):
        return self.client().volumes.update(volume_id, **kwargs)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def attach(self, volume, instance_uuid, mountpoint, mode='rw',
               host_name=None):
        return self.client().volumes.attach(volume, instance_uuid,
                                            mountpoint, mode=mode,
                                            host_name=host_name)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def detach(self, volume, attachment_uuid):
        return self.client().volumes.detach(volume, attachment_uuid)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_snapshot(self, snapshot):
        try:
            return self.client().volume_snapshots.get(snapshot)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='VolumeSnapshot',
                                           name=snapshot)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_volume_snapshot_by_name(self, snap_name):
        snapshots = self.client().volume_snapshots.list(
            search_opts={'name': snap_name})
        if len(snapshots) > 0:
            return snapshots[0]
        else:
            return None

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def get_snapshot_by_caa_snap_id(self, caa_snap_id):
        snap_list = self.client().volume_snapshots.list()
        if snap_list is None or len(snap_list) <= 0:
            return None

        for snap in snap_list:
            if hasattr(snap, 'metadata'):
                temp_id = snap.metadata.get('tag:caa_snapshot_id', None)
                if temp_id == caa_snap_id:
                    return snap
        return None

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def create_snapshot(self, volume_id, force=False, name=None,
                        description=None, metadata=None):
        return self.client().volume_snapshots.create(volume_id, force=force,
                                                     name=name,
                                                     description=description,
                                                     metadata=metadata)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def delete_snapshot(self, snapshot, force=False):
        return self.client().volume_snapshots.delete(snapshot, force=force)

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def update_snapshot(self, snapshot_id, **kwargs):
        return self.client().volume_snapshots.update(snapshot_id, **kwargs)

    @retry(stop_max_attempt_number=900,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_create_snapshot_complete(self, snap_id):
        snap = self.client().volume_snapshots.get(snap_id)
        if snap.status in ('creating'):
            LOG.debug("Snapshot %(id)s is being created - "
                      "status: %(status)s" % {'id': snap_id,
                                              'status': snap.status})
            return False

        if snap.status != 'available':
            LOG.debug("create failed - snapshot %(snap)s is "
                      "in %(status)s status" % {"snap": snap_id,
                                                "status": snap.status})
            raise exception.ResourceUnknownStatus(
                resource_status=snap.status,
                result=_('Snapshot create failed'))

        LOG.info(_LI('creating snapshot %(id)s complete'), {'id': snap_id})
        return True

    @retry(stop_max_attempt_number=900,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_delete_snapshot_complete(self, snap_id):
        try:
            snap = self.client().volume_snapshots.get(snap_id)
        except Exception as ex:
            if not self.ignore_not_found(ex):
                raise
            return True
        if snap.status in ('deleting'):
            LOG.debug("Snapshot %(id)s is being deleted - "
                      "status: %(status)s" % {'id': snap_id,
                                              'status': snap.status})
            return False

        if snap.status == 'error':
            LOG.debug("delete failed - snapshot %(snap)s is "
                      "in %(status)s status" % {"snap": snap_id,
                                                "status": snap.status})
            raise exception.ResourceUnknownStatus(
                resource_status=snap.status,
                result=_('Snapshot delete failed'))

        LOG.info(_LI('delete snapshot %(id)s complete'), {'id': snap_id})
        return True

    @retry(stop_max_attempt_number=max(CLIENT_RETRY_LIMIT + 1, 0),
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def upload_to_image(self, volume, force, image_name, container_format=None,
                        disk_format=None):
        return self.client().volumes.upload_to_image(volume, force, image_name,
                                             container_format, disk_format)

    @retry(stop_max_attempt_number=900,
           wait_fixed=2000,
           retry_on_result=client_plugin.retry_if_result_is_false,
           retry_on_exception=client_plugin.retry_if_ignore_exe)
    @wrap_auth_failed
    def check_upload_image_volume_complete(self, volume):

        LOG.info(_LI("wait volume(%s) upload image complete"), volume)
        by_status = ['uploading']
        expect_status = []
        not_expect_status = ["error"]
        return self.check_opt_volume_complete("upload_image", volume, by_status,
                                              expect_status, not_expect_status)

