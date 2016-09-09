# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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
Handles all requests relating to volumes + cinder.
"""

import collections
import copy
import functools
import sys
import time

from cinderclient import client as cinder_client
from cinderclient import exceptions as cinder_exception
from cinderclient.v1 import client as v1_client
from keystoneauth1 import exceptions as keystone_exception
from oslo_log import log as logging
from oslo_utils import excutils
from oslo_utils import strutils
import six

from jacket import conf
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LE
from jacket.i18n import _LW


CONF = conf.CONF
CINDER_OPT_GROUP = 'fs_cinder'

LOG = logging.getLogger(__name__)
DEFAULT_REGION_NAME = "RegionOne"
DEFAULT_CATALOG_INFO = {"1": {"service_type": "volume",
                              "service_name": "cinder",
                              "endpoint_type": "publicURL"},
                        "2": {"service_type": "volumev2",
                              "service_name": "cinderv2",
                              "endpoint_type": "publicURL"},
                        }


def cinderclient(context, version=None, username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None, endpoint_type=None,
                 region_name=None, *args, **kwargs):

    if version is None:
        version = CONF.fs_cinder.default_version

    if version not in DEFAULT_CATALOG_INFO.keys():
        raise exception.FsCinderVersionNotSupport(version=version)

    if not username or not password or not project_id or not auth_url:
        raise exception.FsCinderNotUserOrPass()

    if not service_type:
        service_type = DEFAULT_CATALOG_INFO[version]["service_type"]

    if not service_name:
        service_name = DEFAULT_CATALOG_INFO[version]["service_name"]

    if not endpoint_type:
        endpoint_type = DEFAULT_CATALOG_INFO[version]["endpoint_type"]

    if not region_name:
        region_name = DEFAULT_REGION_NAME

    return cinder_client.Client(version, username=username, api_key=password,
                                project_id=project_id, auth_url=auth_url,
                                service_type=service_type, service_name=service_name,
                                endpoint_type=endpoint_type, region_name=region_name,
                                *args, **kwargs)


def _untranslate_volume_summary_view(context, vol):
    """Maps keys for volumes summary view."""
    d = {}
    d['id'] = vol.id
    d['status'] = vol.status
    d['size'] = vol.size
    d['availability_zone'] = vol.availability_zone
    d['created_at'] = vol.created_at

    # TODO(jdg): The calling code expects attach_time and
    #            mountpoint to be set. When the calling
    #            code is more defensive this can be
    #            removed.
    d['attach_time'] = ""
    d['mountpoint'] = ""
    d['multiattach'] = getattr(vol, 'multiattach', False)

    if vol.attachments:
        d['attachments'] = collections.OrderedDict()
        for attachment in vol.attachments:
            a = {attachment['server_id']:
                 {'attachment_id': attachment.get('attachment_id'),
                  'mountpoint': attachment.get('device')}
                 }
            d['attachments'].update(a.items())

        d['attach_status'] = 'attached'
    else:
        d['attach_status'] = 'detached'
    # NOTE(dzyu) volume(fs_cinder) v2 API uses 'name' instead of 'display_name',
    # and use 'description' instead of 'display_description' for volume.
    if hasattr(vol, 'display_name'):
        d['display_name'] = vol.display_name
        d['display_description'] = vol.display_description
    else:
        d['display_name'] = vol.name
        d['display_description'] = vol.description
    # TODO(jdg): Information may be lost in this translation
    d['volume_type_id'] = vol.volume_type
    d['snapshot_id'] = vol.snapshot_id
    d['bootable'] = strutils.bool_from_string(vol.bootable)
    d['volume_metadata'] = {}
    for key, value in vol.metadata.items():
        d['volume_metadata'][key] = value

    if hasattr(vol, 'volume_image_metadata'):
        d['volume_image_metadata'] = copy.deepcopy(vol.volume_image_metadata)

    return d


def _untranslate_snapshot_summary_view(context, snapshot):
    """Maps keys for snapshots summary view."""
    d = {}

    d['id'] = snapshot.id
    d['status'] = snapshot.status
    d['progress'] = snapshot.progress
    d['size'] = snapshot.size
    d['created_at'] = snapshot.created_at

    # NOTE(dzyu) volume(fs_cinder) v2 API uses 'name' instead of 'display_name',
    # 'description' instead of 'display_description' for snapshot.
    if hasattr(snapshot, 'display_name'):
        d['display_name'] = snapshot.display_name
        d['display_description'] = snapshot.display_description
    else:
        d['display_name'] = snapshot.name
        d['display_description'] = snapshot.description

    d['volume_id'] = snapshot.volume_id
    d['project_id'] = snapshot.project_id
    d['volume_size'] = snapshot.size

    return d


def translate_cinder_exception(method):
    """Transforms a cinder exception but keeps its traceback intact."""
    @functools.wraps(method)
    def wrapper(self, ctx, *args, **kwargs):
        try:
            res = method(self, ctx, *args, **kwargs)
        except (cinder_exception.ConnectionError,
                keystone_exception.ConnectionError):
            exc_type, exc_value, exc_trace = sys.exc_info()
            exc_value = exception.FsCinderConnectFailed(
                reason=six.text_type(exc_value))
            six.reraise(exc_value, None, exc_trace)
        except (keystone_exception.BadRequest,
                cinder_exception.BadRequest):
            exc_type, exc_value, exc_trace = sys.exc_info()
            exc_value = exception.InvalidInput(
                reason=six.text_type(exc_value))
            six.reraise(exc_value, None, exc_trace)
        except (keystone_exception.Forbidden,
                cinder_exception.Forbidden):
            exc_type, exc_value, exc_trace = sys.exc_info()
            exc_value = exception.Forbidden(message=six.text_type(exc_value))
            six.reraise(exc_value, None, exc_trace)
        return res
    return wrapper


def translate_volume_exception(method):
    """Transforms the exception for the volume but keeps its traceback intact.
    """
    def wrapper(self, ctx, volume_id, *args, **kwargs):
        try:
            res = method(self, ctx, volume_id, *args, **kwargs)
        except (cinder_exception.ClientException,
                keystone_exception.ClientException):
            exc_type, exc_value, exc_trace = sys.exc_info()
            if isinstance(exc_value, (keystone_exception.NotFound,
                                      cinder_exception.NotFound)):
                exc_value = exception.FsVolumeNotFound(volume_id=volume_id)
            six.reraise(exc_value, None, exc_trace)
        return res
    return translate_cinder_exception(wrapper)


def translate_snapshot_exception(method):
    """Transforms the exception for the snapshot but keeps its traceback
       intact.
    """
    def wrapper(self, ctx, snapshot_id, *args, **kwargs):
        try:
            res = method(self, ctx, snapshot_id, *args, **kwargs)
        except (cinder_exception.ClientException,
                keystone_exception.ClientException):
            exc_type, exc_value, exc_trace = sys.exc_info()
            if isinstance(exc_value, (keystone_exception.NotFound,
                                      cinder_exception.NotFound)):
                exc_value = exception.FsSnapshotNotFound(snapshot_id=snapshot_id)
            six.reraise(exc_value, None, exc_trace)
        return res
    return translate_cinder_exception(wrapper)


class FsCinderClientWrapper(object):
    """fs cinder client wrapper class that implements retries."""

    def __init__(self, context=None, is_static=True, version=None,
                 username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None,
                 endpoint_type=None, region_name=None,
                 *args, **kwargs):

        self.context = context
        self.version = version
        self.username = username
        self.password = password
        self.project_id = project_id
        self.auth_url = auth_url
        self.service_type = service_type
        self.service_name = service_name
        self.endpoint_type = endpoint_type
        self.region_name = region_name
        self.args = args
        self.kwargs = kwargs
        if is_static:
            self.client = self._create_fs_cinder_client()
        else:
            self.client = None

        if CONF.fs_cinder.num_retries < 0:
            LOG.warning(_LW(
                "num_retries shouldn't be a negative value. "
                "The number of retries will be set to 0 until this is"
                "corrected in the jacket.conf."))
            CONF.set_override('num_retries', 0, 'fs_cinder')

    def _create_fs_cinder_client(self):
        """Create a client that we'll use for every call."""
        return cinderclient(self.context, self.version, self.username,
                            self.password, self.project_id, self.auth_url,
                            self.service_type, self.service_name,
                            self.endpoint_type, self.region_name,
                            *(self.args), **(self.kwargs))

    def call(self, context, method, *args, **kwargs):
        """Call a glance client method.

        If we get a connection error,
        retry the request according to CONF.glance_num_retries.
        """
        version = self.version

        retry_excs = (cinder_exception.ClientException)
        num_attempts = 1 + CONF.fs_cinder.num_retries

        for attempt in range(1, num_attempts + 1):
            client = self.client or self._create_fs_cinder_client(context,
                                                                version)
            try:
                controller = getattr(client,
                                     kwargs.pop('controller', 'volumes'))
                return getattr(controller, method)(*args, **kwargs)
            except retry_excs as e:
                extra = "retrying"
                error_msg = _LE("Error contacting cinder server "
                                " for '%(method)s', "
                                "%(extra)s.")
                if attempt == num_attempts:
                    extra = 'done trying'
                    LOG.exception(error_msg, {'method': method,
                                              'extra': extra})
                    raise exception.FsCinderConnectFailed()

                LOG.exception(error_msg, {'method': method,
                                          'extra': extra})
                time.sleep(1)


class FsCinderService(object):
    """API for interacting with the volume manager."""

    def __init__(self, context=None, is_static=True, version=None,
                 username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None,
                 endpoint_type=None, region_name=None,
                 *args, **kwargs):
        self.client = FsCinderClientWrapper(context, is_static, version,
                                            username, password, project_id,
                                            auth_url, service_type, service_name,
                                            endpoint_type, region_name, *args, **kwargs)

    @translate_volume_exception
    def get(self, context, volume_id):
        item = self.client.call(context, 'get', volume_id)
        return _untranslate_volume_summary_view(context, item)

    @translate_cinder_exception
    def get_all(self, context, search_opts=None):
        search_opts = search_opts or {}
        items = self.client.call(context, 'list', detailed=True,
                                search_opts=search_opts)

        rval = []

        for item in items:
            rval.append(_untranslate_volume_summary_view(context, item))

        return rval

    def check_attached(self, context, volume):
        if volume['status'] != "in-use":
            msg = _("volume '%(vol)s' status must be 'in-use'. Currently in "
                    "'%(status)s' status") % {"vol": volume['id'],
                                              "status": volume['status']}
            raise exception.FsInvalidVolume(reason=msg)

    def check_attach(self, context, volume, instance=None):
        # TODO(vish): abstract status checking?
        if volume['status'] != "available":
            msg = _("volume '%(vol)s' status must be 'available'. Currently "
                    "in '%(status)s'") % {'vol': volume['id'],
                                          'status': volume['status']}
            raise exception.FsInvalidVolume(reason=msg)
        if volume['attach_status'] == "attached":
            msg = _("volume %s already attached") % volume['id']
            raise exception.FsInvalidVolume(reason=msg)

    def check_detach(self, context, volume, instance=None):
        # TODO(vish): abstract status checking?
        if volume['status'] == "available":
            msg = _("volume %s already detached") % volume['id']
            raise exception.FsInvalidVolume(reason=msg)

        if volume['attach_status'] == 'detached':
            msg = _("Volume must be attached in order to detach.")
            raise exception.FsInvalidVolume(reason=msg)

        # NOTE(ildikov):Preparation for multiattach support, when a volume
        # can be attached to multiple hosts and/or instances,
        # so just check the attachment specific to this instance
        if instance is not None and instance.uuid not in volume['attachments']:
            # TODO(ildikov): change it to a better exception, when enable
            # multi-attach.
            raise exception.FsVolumeUnattached(volume_id=volume['id'])

    @translate_volume_exception
    def reserve_volume(self, context, volume_id):
        self.client.call(context, 'reserve', volume_id)

    @translate_volume_exception
    def unreserve_volume(self, context, volume_id):
        self.client.call(context, 'unreserve', volume_id)

    @translate_volume_exception
    def begin_detaching(self, context, volume_id):
        self.client.call(context, 'begin_detaching', volume_id)

    @translate_volume_exception
    def roll_detaching(self, context, volume_id):
        self.client.call(context, 'roll_detaching', volume_id)

    @translate_volume_exception
    def attach(self, context, volume_id, instance_uuid, mountpoint, mode='rw'):
        self.client.call(context, 'attach', volume_id, instance_uuid,
                                             mountpoint, mode=mode)

    @translate_volume_exception
    def detach(self, context, volume_id, instance_uuid=None,
               attachment_id=None):
        if attachment_id is None:
            volume = self.get(context, volume_id)
            if volume['multiattach']:
                attachments = volume.get('attachments', {})
                if instance_uuid:
                    attachment_id = attachments.get(instance_uuid, {}).\
                            get('attachment_id')
                    if not attachment_id:
                        LOG.warning(_LW("attachment_id couldn't be retrieved "
                                        "for volume %(volume_id)s with "
                                        "instance_uuid %(instance_id)s. The "
                                        "volume has the 'multiattach' flag "
                                        "enabled, without the attachment_id "
                                        "Cinder most probably cannot perform "
                                        "the detach."),
                                    {'volume_id': volume_id,
                                     'instance_id': instance_uuid})
                else:
                    LOG.warning(_LW("attachment_id couldn't be retrieved for "
                                    "volume %(volume_id)s. The volume has the "
                                    "'multiattach' flag enabled, without the "
                                    "attachment_id Cinder most probably "
                                    "cannot perform the detach."),
                                {'volume_id': volume_id})

        self.client.call(context, 'detach', volume_id, attachment_id)

    @translate_volume_exception
    def initialize_connection(self, context, volume_id, connector):
        try:
            connection_info = self.client.call(context, 'initialize_connection',
                                               volume_id, connector)

            connection_info['connector'] = connector
            return connection_info
        except cinder_exception.ClientException as ex:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE('Initialize connection failed for volume '
                              '%(vol)s on host %(host)s. Error: %(msg)s '
                              'Code: %(code)s. Attempting to terminate '
                              'connection.'),
                          {'vol': volume_id,
                           'host': connector.get('host'),
                           'msg': six.text_type(ex),
                           'code': ex.code})
                try:
                    self.terminate_connection(context, volume_id, connector)
                except Exception as exc:
                    LOG.error(_LE('Connection between volume %(vol)s and host '
                                  '%(host)s might have succeeded, but attempt '
                                  'to terminate connection has failed. '
                                  'Validate the connection and determine if '
                                  'manual cleanup is needed. Error: %(msg)s '
                                  'Code: %(code)s.'),
                              {'vol': volume_id,
                               'host': connector.get('host'),
                               'msg': six.text_type(exc),
                               'code': (
                                exc.code if hasattr(exc, 'code') else None)})

    @translate_volume_exception
    def terminate_connection(self, context, volume_id, connector):
        return self.client.call(context, 'terminate_connection',
                                volume_id, connector)

    @translate_cinder_exception
    def create(self, context, size, name, description, snapshot=None,
               image_id=None, volume_type=None, metadata=None,
               availability_zone=None):

        if snapshot is not None:
            snapshot_id = snapshot['id']
        else:
            snapshot_id = None

        kwargs = dict(snapshot_id=snapshot_id,
                      volume_type=volume_type,
                      user_id=context.user_id,
                      project_id=context.project_id,
                      availability_zone=availability_zone,
                      metadata=metadata,
                      imageRef=image_id)

        if isinstance(self.client, v1_client.Client):
            kwargs['display_name'] = name
            kwargs['display_description'] = description
        else:
            kwargs['name'] = name
            kwargs['description'] = description

        try:
            item = self.client.call(context, "create", size, **kwargs)
            return _untranslate_volume_summary_view(context, item)
        except cinder_exception.OverLimit:
            raise exception.FsOverQuota(overs='volumes')

    @translate_volume_exception
    def delete(self, context, volume_id):
        self.client.call(context, "delete", volume_id)

    @translate_volume_exception
    def update(self, context, volume_id, fields):
        raise NotImplementedError()

    @translate_snapshot_exception
    def get_snapshot(self, context, snapshot_id):
        item = self.client.call(context, "get", snapshot_id, controller="volume_snapshots")
        return _untranslate_snapshot_summary_view(context, item)

    @translate_cinder_exception
    def get_all_snapshots(self, context):
        items = self.client.call(context, "list", detailed=True,
                                controller="volume_snapshots")
        rvals = []

        for item in items:
            rvals.append(_untranslate_snapshot_summary_view(context, item))

        return rvals

    @translate_volume_exception
    def create_snapshot(self, context, volume_id, name, description):
        item = self.client.call(context, "create", volume_id,
                                 False, name, description,
                                controller="volume_snapshots")
        return _untranslate_snapshot_summary_view(context, item)

    @translate_volume_exception
    def create_snapshot_force(self, context, volume_id, name, description):
        item = self.client.call(context, "create", volume_id,
                                True, name, description,
                                controller="volume_snapshots")

        return _untranslate_snapshot_summary_view(context, item)

    @translate_snapshot_exception
    def delete_snapshot(self, context, snapshot_id):
        self.client.call(context, "delete", snapshot_id,
                         controller="volume_snapshots")

    @translate_cinder_exception
    def get_volume_encryption_metadata(self, context, volume_id):
        return self.client.call(context, "get_encryption_metadata", volume_id)

    @translate_snapshot_exception
    def update_snapshot_status(self, context, snapshot_id, status):
        vs = cinderclient(context).volume_snapshots

        # '90%' here is used to tell Cinder that Nova is done
        # with its portion of the 'creating' state. This can
        # be removed when we are able to split the Cinder states
        # into 'creating' and a separate state of
        # 'creating_in_nova'. (Same for 'deleting' state.)

        self.client.call(context, "update_snapshot_status", snapshot_id,
                         {'status': status,
                          'progress': '90%'},
                         controller="volume_snapshots")
