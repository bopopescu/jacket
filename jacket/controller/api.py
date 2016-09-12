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


import base64
import copy
import functools
import re
import string
import uuid

from oslo_config import cfg
from oslo_log import log as logging
from oslo_messaging import exceptions as oslo_exceptions
from oslo_serialization import jsonutils
from oslo_utils import excutils
from oslo_utils import strutils
from oslo_utils import timeutils
from oslo_utils import units
from oslo_utils import uuidutils
import six
from six.moves import range


from jacket import exception
import jacket.policy
from jacket import base_rpc
from jacket.db import base
from jacket.db import api as db_api


LOG = logging.getLogger(__name__)

get_notifier = functools.partial(base_rpc.get_notifier, service='jacket')

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

        super(API, self).__init__(**kwargs)
