import socket

from oslo_config import cfg
from oslo_utils import netutils

CONF = cfg.CONF


netconf_opts = [
    cfg.StrOpt('my_ip',
               default=netutils.get_my_ipv4(),
               help='IP address of this host'),
    cfg.StrOpt('my_block_storage_ip',
               default='$my_ip',
               help='Block storage IP address of this host'),
    cfg.StrOpt('host',
               default=socket.gethostname(),
               help='Name of this node.  This can be an opaque identifier.  '
                    'It is not necessarily a hostname, FQDN, or IP address. '
                    'However, the node name must be valid within '
                    'an AMQP key, and if using ZeroMQ, a valid '
                    'hostname, FQDN, or IP address'),
    cfg.BoolOpt('use_ipv6',
                default=False,
                help='Use IPv6'),
]

CONF.register_opts(netconf_opts)
