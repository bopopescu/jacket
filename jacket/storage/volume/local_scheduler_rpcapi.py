# Copyright 2012, Red Hat, Inc.
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
Client side of the scheduler manager RPC API.
"""

from oslo_config import cfg
from oslo_serialization import jsonutils

from jacket.i18n import _
from jacket.objects import storage
from jacket.storage import quota
from jacket.storage import exception
from jacket.storage.volume import rpcapi as volume_rpcapi

CONF = cfg.CONF
QUOTAS = quota.QUOTAS

class SchedulerAPI(object):

    def retype(self, context, topic, volume_id,
               request_spec=None, filter_properties=None, volume=None):

        """Schedule the modification of a volume's type.

        :param context: the request context
        :param topic: the topic listened on
        :param volume_id: the ID of the volume to retype
        :param request_spec: parameters for this retype request
        :param filter_properties: parameters to filter by
        :param volume: the volume object to retype
        """

        # FIXME(thangp): Remove this in v2.0 of RPC API.
        if volume is None:
            # For older clients, mimic the old behavior and look up the
            # volume by its volume_id.
            volume = storage.Volume.get_by_id(context, volume_id)


        def _retype_volume_set_error(self, context, ex, request_spec,
                                     volume_ref, msg, reservations):
            if reservations:
                QUOTAS.rollback(context, reservations)
            previous_status = (
                volume_ref.previous_status or volume_ref.status)
            volume_state = {'volume_state': {'status': previous_status}}
            self._set_volume_state_and_notify('retype', volume_state,
                                              context, ex, request_spec, msg)


        reservations = request_spec.get('quota_reservations')
        old_reservations = request_spec.get('old_reservations', None)
        new_type = request_spec.get('volume_type')
        if new_type is None:
            msg = _('New volume type not specified in request_spec.')
            ex = exception.ParameterNotFound(param='volume_type')
            _retype_volume_set_error(self, context, ex, request_spec,
                                     volume, msg, reservations)

        # Default migration policy is 'never'
        migration_policy = request_spec.get('migration_policy')
        if not migration_policy:
            migration_policy = 'never'

        tgt_host = None

        volume_rpcapi.VolumeAPI().retype(context, volume,
                                         new_type['id'], tgt_host,
                                         migration_policy,
                                         reservations,
                                         old_reservations)