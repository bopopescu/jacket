"""Handles all processes to clouds.

The :py:class:`WorkerManager` class is a :py:class:`jacket.manager.Manager` that
handles RPC calls relating to creating instances.  It is responsible for
building a disk image, launching it via the underlying virtualization driver,
responding to calls to check its state, attaching persistent storage, and
terminating it.

"""

import functools

from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging

from jacket.compute import exception
from jacket import rpc
from jacket.compute.cloud import manager as com_manager
from jacket.storage.volume import manager as vol_manager
from jacket import manager

CONF = cfg.CONF

LOG = logging.getLogger(__name__)

get_notifier = functools.partial(rpc.get_notifier, service='worker')
wrap_exception = functools.partial(exception.wrap_exception,
                                   get_notifier=get_notifier)


class WorkerManager(manager.Manager):
    """Manages the running instances from creation to destruction."""
    RPC_API_VERSION = '1.0'

    target = messaging.Target(version="1.0")

    def __init__(self, *args, **kwargs):
        """Load configuration options and connect to the cloud."""
        super(WorkerManager, self).__init__(service_name="worker", *args, **kwargs)
        self.compute_manager = com_manager.ComputeManager()

        backend = None

        if CONF.enabled_backends:
            for backend in CONF.enabled_backends:
                break

        self.storage_manager = vol_manager.VolumeManager(service_name=backend)
        self.additional_endpoints.append(self.compute_manager)
        self.additional_endpoints.append(self.storage_manager)

        # use storage manage rpc version
        self.RPC_API_VERSION = self.storage_manager.RPC_API_VERSION

    def init_host(self):
        """Initialization for a standalone cloud service."""

        # super(WorkerManager, self).init_host()
        # jacket init host TODO

        self.compute_manager.init_host()
        self.storage_manager.init_host()

    def cleanup_host(self):
        # super(WorkerManager, self).cleanup_host()
        # jacket cleanup host TODO
        self.compute_manager.cleanup_host()
        self.storage_manager.cleanup_host()

    def pre_start_hook(self):
        # super(WorkerManager, self).pre_start_hook()

        # jacket pre_start_hook TODO
        self.compute_manager.pre_start_hook()
        self.storage_manager.pre_start_hook()

    def post_start_hook(self):
        # super(WorkerManager, self).post_start_hook()

        # jacket post_start_hook TODO
        self.compute_manager.post_start_hook()
        self.storage_manager.post_start_hook()

    def reset(self):
        # super(WorkerManager, self).reset()

        # jacket post_start_hook TODO
        self.compute_manager.reset()
        self.storage_manager.reset()
