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

import functools

from oslo_config import cfg
from oslo_log import log as logging

import jacket.policy
from jacket import rpc
from jacket.db import base
from jacket.db.hybrid_cloud import api as db_api
from jacket.worker import rpcapi as worker_rpcapi

LOG = logging.getLogger(__name__)

get_notifier = functools.partial(rpc.get_notifier, service='jacket')

CONF = cfg.CONF


def policy_decorator(scope):
    """Check corresponding policy prior of wrapped method to execution."""

    def outer(func):
        @functools.wraps(func)
        def wrapped(self, context, target, *args, **kwargs):
            if not self.skip_policy_check:
                check_policy(context, func.__name__, target, scope)
            return func(self, context, target, *args, **kwargs)

        return wrapped

    return outer


wrap_check_policy = policy_decorator(scope='jacket')


def check_policy(context, action, target, scope='jacket'):
    _action = '%s:%s' % (scope, action)
    jacket.policy.enforce(context, _action, target)


def _diff_dict(orig, new):
    """Return a dict describing how to change orig to new.  The keys
    correspond to values that have changed; the value will be a list
    of one or two elements.  The first element of the list will be
    either '+' or '-', indicating whether the key was updated or
    deleted; if the key was updated, the list will contain a second
    element, giving the updated value.
    """
    # Figure out what keys went away
    result = {k: ['-'] for k in set(orig.keys()) - set(new.keys())}
    # Compute the updates
    for key, value in new.items():
        if key not in orig or value != orig[key]:
            result[key] = ['+', value]
    return result


class API(base.Base):
    """API for interacting with the compute manager."""

    def __init__(self, skip_policy_check=False, **kwargs):
        self.skip_policy_check = skip_policy_check
        self.db_api = db_api
        self.worker_rpcapi = worker_rpcapi.JacketAPI()

        super(API, self).__init__(**kwargs)

    def image_mapper_all(self, context):
        return self.db_api.image_mapper_all(context)

    def image_mapper_get(self, context, image_id, project_id=None):
        return self.db_api.image_mapper_get(context, image_id, project_id)

    def image_mapper_create(self, context, image_id, project_id, values):
        return self.db_api.image_mapper_create(context, image_id, project_id,
                                               values)

    def image_mapper_update(self, context, image_id, project_id, values):
        set_properties = values.get("set_properties", {})
        unset_properties = values.get("unset_properties", {})
        image_info = self.image_mapper_get(context, image_id, project_id)

        for key, value in set_properties.iteritems():
            image_info[key] = value
        for key in unset_properties.keys():
            if key in image_info:
                del image_info[key]

        del image_info['image_id']
        del image_info['project_id']

        return self.db_api.image_mapper_update(context, image_id, project_id,
                                               image_info, delete=True)

    def image_mapper_delete(self, context, image_id, project_id=None):
        return self.db_api.image_mapper_delete(context, image_id, project_id)

    def flavor_mapper_all(self, context):
        return self.db_api.flavor_mapper_all(context)

    def flavor_mapper_get(self, context, flavor_id, project_id=None):
        return self.db_api.flavor_mapper_get(context, flavor_id, project_id)

    def flavor_mapper_create(self, context, flavor_id, project_id, values):
        return self.db_api.flavor_mapper_create(context, flavor_id, project_id,
                                                values)

    def flavor_mapper_update(self, context, flavor_id, project_id, values):
        set_properties = values.get("set_properties", {})
        unset_properties = values.get("unset_properties", {})
        flavor_info = self.flavor_mapper_get(context, flavor_id, project_id)
        for key, value in set_properties.iteritems():
            flavor_info[key] = value
        for key in unset_properties.keys():
            if key in flavor_info:
                del flavor_info[key]

        del flavor_info['flavor_id']
        del flavor_info['project_id']

        return self.db_api.flavor_mapper_update(context, flavor_id, project_id,
                                                flavor_info, delete=True)

    def flavor_mapper_delete(self, context, flavor_id, project_id=None):
        return self.db_api.flavor_mapper_delete(context, flavor_id, project_id)

    def project_mapper_all(self, context):
        return self.db_api.project_mapper_all(context)

    def project_mapper_get(self, context, project_id):
        return self.db_api.project_mapper_get(context, project_id)

    def project_mapper_create(self, context, project_id, values):
        return self.db_api.project_mapper_create(context, project_id, values)

    def project_mapper_update(self, context, project_id, values):
        set_properties = values.get("set_properties", {})
        unset_properties = values.get("unset_properties", {})
        project_info = self.project_mapper_get(context, project_id)
        for key, value in set_properties.iteritems():
            project_info[key] = value
        for key in unset_properties.keys():
            if key in project_info:
                del project_info[key]

        del project_info['project_id']

        return self.db_api.project_mapper_update(context, project_id, project_info,
                                                 delete=True)

    def project_mapper_delete(self, context, project_id):
        return self.db_api.project_mapper_delete(context, project_id)

    def sub_flavor_detail(self, context):
        return self.worker_rpcapi.sub_flavor_detail(context)

    def sub_vol_type_detail(self, context):
        return self.worker_rpcapi.sub_vol_type_detail(context)
