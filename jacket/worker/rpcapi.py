"""
Client side of the jacket worker RPC API.
"""

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from jacket.compute import exception
from jacket.i18n import _
from jacket import rpc
from jacket.objects import base as objects_base

rpcapi_opts = [
    cfg.StrOpt('jacket_topic',
               default='jacket-worker',
               help='The topic compute nodes listen on'),
]

CONF = cfg.CONF
CONF.register_opts(rpcapi_opts)

rpcapi_cap_opt = cfg.StrOpt('jacket',
        help='Set a version cap for messages sent to jacket services. '
             'Set this option to "auto" if you want to let the jacket RPC '
             'module automatically determine what version to use based on '
             'the service versions in the deployment. '
             'Otherwise, you can set this to a specific version to pin this '
             'service to messages at a particular level. '
             'All services of a single type (i.e. jacket) should be '
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

    API version history:

        * 1.0 - Initial version.
    '''

    VERSION_ALIASES = {
        'apple': '1.0',
    }

    def __init__(self):
        super(JacketAPI, self).__init__()
        target = messaging.Target(topic=CONF.jacket_topic, version='1.0')
        serializer = objects_base.JacketObjectSerializer()
        self.client = self.get_client(target, '1.0', serializer)

    def get_client(self, target, version_cap, serializer):
        return rpc.get_client(target,
                              version_cap=version_cap,
                              serializer=serializer)

    def sub_flavor_detail(self, ctxt):
        version = "1.0"
        return self.client.call(ctxt, 'sub_flavor_detail')

    def sub_vol_type_detail(self, ctxt):
        version = "1.0"
        return self.client.call(ctxt, 'sub_vol_type_detail')
