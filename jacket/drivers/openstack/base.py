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

from oslo_log import log as logging
import six

from jacket.compute import image
from jacket.db.extend import api as caa_db_api
from jacket import context as req_context
from jacket.drivers.openstack.clients import os_context
from jacket.drivers.openstack.clients import nova as novaclient
from jacket.drivers.openstack.clients import cinder as cinderclient
from jacket.drivers.openstack.clients import glance as glanceclient
from jacket.drivers.openstack import exception_ex
from jacket import exception

LOG = logging.getLogger(__name__)


class OsDriver(object):
    def __init__(self, *args, **kwargs):
        LOG.debug("+++++++++++++++++++++++++++++")

        super(OsDriver, self).__init__(*args, **kwargs)

    def os_novaclient(self, context=None):
        if self._os_novaclient is None:
            oscontext = os_context.OsClientContext(
                context, version='2'
            )
            self._os_novaclient = novaclient.NovaClientPlugin(oscontext)

        return self._os_novaclient

    def os_cinderclient(self, context=None):
        if self._os_cinderclient is None:
            oscontext = os_context.OsClientContext(
                context, version='2'
            )
            self._os_cinderclient = cinderclient.CinderClientPlugin(oscontext)

        return self._os_cinderclient

    def os_glanceclient(self, context=None):
        if self._os_glanceclient is None:
            oscontext = os_context.OsClientContext(
                context, version='2'
            )
            self._os_glanceclient = glanceclient.GlanceClientPlugin(oscontext)

        return self._os_glanceclient

    def _get_project_mapper(self, context, project_id=None):
        if project_id is None:
            project_id = 'default'

        project_mapper = self.caa_db_api.project_mapper_get(context, project_id)
        if not project_mapper:
            project_mapper = self.caa_db_api.project_mapper_get(context,
                                                                'default')

        if not project_mapper:
            raise exception_ex.AccountNotConfig()

        return project_mapper

    def _get_provider_instance_id(self, context, caa_instance_id):
        instance_mapper = self.caa_db_api.instance_mapper_get(context,
                                                              caa_instance_id)
        return instance_mapper.get('provider_instance_id', None)

    def _get_provider_instance(self, context=None, hybrid_instance=None):
        if not context:
            context = req_context.RequestContext(
                is_admin=True, project_id=hybrid_instance.project_id)

        provider_instance_id = self._get_provider_instance_id(context,
                                                              hybrid_instance.uuid)
        if provider_instance_id:
            return self.os_novaclient(context).get_server(provider_instance_id)

        server = self.os_novaclient(context).get_server_by_caa_instance_id(
            hybrid_instance.uuid)
        if server is None:
            raise exception.EntityNotFound(entity='Server',
                                           name=hybrid_instance.uuid)
        return server

    def _get_provider_base_image_id(self, context, image_id=None):
        
        project_mapper = self._get_project_mapper(context, context.project_id)
        return project_mapper.get("base_linux_image", None)

    def _get_provider_image_id(self, context, image_id):
        image_mapper = self.caa_db_api.image_mapper_get(context, image_id)
        sub_image_id = image_mapper.get("provider_image_id")

        return sub_image_id

    def _get_provider_volume_name(self, volume_name, volume_id):
        if not volume_name:
            volume_name = 'volume'
        return '@'.join([volume_name, volume_id])

    def _get_provider_volume_id(self, context, caa_volume_id):
        volume_mapper = self.caa_db_api.volume_mapper_get(context,
                                                          caa_volume_id)
        provider_volume_id = volume_mapper.get('provider_volume_id', None)
        if provider_volume_id:
            return provider_volume_id

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

    def _get_mountpoint_for_volume(self, provider_volume):
        LOG.debug('start to _get_mountpoint_for_volume: %s' % provider_volume)
        device = None
        attachments = provider_volume.attachments
        LOG.debug('attachments: %s' % attachments)
        for attachment in attachments:
            volume_id = attachment.get('volume_id')
            tmp_device = attachment.get('device')
            if volume_id == provider_volume.id:
                device = tmp_device
                break
            else:
                continue

        return device
