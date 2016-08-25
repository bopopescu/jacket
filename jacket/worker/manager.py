"""Handles all processes to clouds.

The :py:class:`WorkerManager` class is a :py:class:`jacket.manager.Manager` that
handles RPC calls relating to creating instances.  It is responsible for
building a disk image, launching it via the underlying virtualization driver,
responding to calls to check its state, attaching persistent storage, and
terminating it.

"""

import functools
from oslo_log import log as logging
import oslo_messaging as messaging
from jacket.compute import exception
from jacket import rpc
from jacket.compute.cloud import manager as com_manager
from jacket.storage.volume import manager as vol_manager

from jacket import manager

LOG = logging.getLogger(__name__)

get_notifier = functools.partial(rpc.get_notifier, service='worker')
wrap_exception = functools.partial(exception.wrap_exception,
                                   get_notifier=get_notifier)


class WorkerManager(com_manager.ComputeManager, vol_manager.VolumeManager):
    """Manages the running instances from creation to destruction."""
    RPC_API_VERSION = '1.0'

    target = messaging.Target(version="1.0")

    def __init__(self, *args, **kwargs):
        """Load configuration options and connect to the cloud."""
        super(WorkerManager, self).__init__(service_name="worker", *args, **kwargs)
        LOG.debug("+++hw, target = %s", self.target)

    def init_host(self):
        """Initialization for a standalone cloud service."""
        super(WorkerManager, self).init_host()

    def cleanup_host(self):
        super(WorkerManager, self).cleanup_host()

    def pre_start_hook(self):
        super(WorkerManager, self).pre_start_hook()

    def post_start_hook(self):
        super(WorkerManager, self).post_start_hook()

    def reset(self):
        super(WorkerManager, self).reset()

#    def compute_test(self, ctxt):
#        LOG.debug("+++hw, compute_test..............................")
