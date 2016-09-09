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

from cinderclient import client as cc
from cinderclient import exceptions
from oslo_log import log as logging

from jacket import conf
from jacket import exception
from jacket.i18n import _
from jacket.i18n import _LI
from jacket.drivers.fs.clients import client_plugin


LOG = logging.getLogger(__name__)

CLIENT_NAME = 'cinder'

CONF = conf.CONF


class CinderClientPlugin(client_plugin.ClientPlugin):

    exceptions_module = exceptions

    service_types = [VOLUME_V2, VOLUME_V3] = ['volumev2', 'volumev3']

    def _create(self):
        version = '2'
        extensions = cc.discover_extensions(self.client_version)

        args = self.context.to_dict()
        args.update(
            {
                'extensions': extensions,
                'http_log_debug': self._get_client_option(CLIENT_NAME,
                                                          'http_log_debug')
            }
        )

        if args.get('version', None):
            version = args.pop('version')

        client = cc.Client(version, **args)
        return client

    def _list_extensions(self):
        extensions = self.client().list_extensions.show_all()
        return set(extension.alias for extension in extensions)

    def has_extension(self, alias):
        """Check if specific extension is present."""
        return alias in self._list_extensions()

    def get_volume(self, volume):
        try:
            return self.client().volumes.get(volume)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Volume', name=volume)

    def get_volume_snapshot(self, snapshot):
        try:
            return self.client().volume_snapshots.get(snapshot)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='VolumeSnapshot',
                                           name=snapshot)

    def get_volume_backup(self, backup):
        try:
            return self.client().backups.get(backup)
        except exceptions.NotFound:
            raise exception.EntityNotFound(entity='Volume backup',
                                           name=backup)

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

    def check_detach_volume_complete(self, vol_id):
        try:
            vol = self.client().volumes.get(vol_id)
        except Exception as ex:
            self.ignore_not_found(ex)
            return True

        if vol.status in ('in-use', 'detaching'):
            LOG.debug('%s - volume still in use' % vol_id)
            return False

        LOG.debug('Volume %(id)s - status: %(status)s' % {
            'id': vol.id, 'status': vol.status})

        if vol.status not in ('available', 'deleting'):
            LOG.debug("Detachment failed - volume %(vol)s "
                      "is in %(status)s status" % {"vol": vol.id,
                                                   "status": vol.status})
            raise exception.ResourceUnknownStatus(
                resource_status=vol.status,
                result=_('Volume detachment failed'))
        else:
            return True

    def check_attach_volume_complete(self, vol_id):
        vol = self.client().volumes.get(vol_id)
        if vol.status in ('available', 'attaching'):
            LOG.debug("Volume %(id)s is being attached - "
                      "volume status: %(status)s" % {'id': vol_id,
                                                     'status': vol.status})
            return False

        if vol.status != 'in-use':
            LOG.debug("Attachment failed - volume %(vol)s is "
                      "in %(status)s status" % {"vol": vol_id,
                                                "status": vol.status})
            raise exception.ResourceUnknownStatus(
                resource_status=vol.status,
                result=_('Volume attachment failed'))

        LOG.info(_LI('Attaching volume %(id)s complete'), {'id': vol_id})
        return True
