"""Generic Node base class for all workers that run for cloud."""

import os
import random
import sys

from oslo_concurrency import processutils
from oslo_config import cfg
from oslo_log import log as logging
import oslo_messaging as messaging
from oslo_service import service
from oslo_utils import importutils

osprofiler_notifier = importutils.try_import('osprofiler.notifier')
profiler = importutils.try_import('osprofiler.profiler')
osprofiler_web = importutils.try_import('osprofiler.web')
profiler_opts = importutils.try_import('osprofiler.opts')

from jacket.compute import baserpc
from jacket.compute import conductor
from jacket.compute import debugger
from jacket import context
from jacket import exception
from jacket.i18n import _, _LE, _LI, _LW
from jacket import objects
from jacket.objects import base as objects_base
from jacket.objects.storage import base as storage_objects_base
from jacket.objects.compute import service as service_obj
from jacket import rpc
from jacket.compute import servicegroup
from jacket import utils
from jacket import version
from jacket.wsgi import base_wsgi

LOG = logging.getLogger(__name__)

service_opts = [
    cfg.StrOpt('worker_manager',
               default='jacket.worker.manager.WorkerManager',
               help='DEPRECATED: Full class name for the Manager for worker'),
    cfg.StrOpt('controller_manager',
               default='jacket.controller.manager.ControllerManager',
               help='DEPRECATED: Full class name for the Manager for controller'),
    cfg.IntOpt('report_interval',
               default=10,
               help='Seconds between nodes reporting state to datastore'),
    cfg.BoolOpt('periodic_enable',
                default=True,
                help='Enable periodic tasks'),
    cfg.IntOpt('periodic_fuzzy_delay',
               default=60,
               help='Range of seconds to randomly delay when starting the'
                    ' periodic task scheduler to reduce stampeding.'
                    ' (Disable by setting to 0)'),
    cfg.ListOpt('enabled_apis',
                default=['osapi_compute', 'metadata', 'osapi_jacket',
                         'osapi_volume'],
                help='A list of APIs to enable by default'),
    cfg.ListOpt('enabled_ssl_apis',
                default=[],
                help='A list of APIs with enabled SSL'),
    cfg.StrOpt('osapi_compute_listen',
               default="0.0.0.0",
               help='The IP address on which the OpenStack API will listen.'),
    cfg.IntOpt('osapi_compute_listen_port',
               default=8774,
               min=1,
               max=65535,
               help='The port on which the OpenStack API will listen.'),
    cfg.IntOpt('osapi_compute_workers',
               help='Number of workers for OpenStack API service. The default '
                    'will be the number of CPUs available.'),
    cfg.StrOpt('metadata_manager',
               default='jacket.api.compute.manager.MetadataManager',
               help='DEPRECATED: OpenStack metadata service manager',
               deprecated_for_removal=True),
    cfg.StrOpt('metadata_listen',
               default="0.0.0.0",
               help='The IP address on which the metadata API will listen.'),
    cfg.IntOpt('metadata_listen_port',
               default=8775,
               min=1,
               max=65535,
               help='The port on which the metadata API will listen.'),
    cfg.IntOpt('metadata_workers',
               help='Number of workers for metadata service. The default will '
                    'be the number of CPUs available.'),
    # NOTE(sdague): Ironic is still using this facility for their HA
    # manager. Ensure they are sorted before removing this.
    cfg.StrOpt('jacket_manager',
               default='jacket.worker.manager.WorkerManager',
               help='DEPRECATED: Full class name for the Manager for jacket',
               deprecated_for_removal=True),
    cfg.StrOpt('console_manager',
               default='jacket.compute.console.manager.ConsoleProxyManager',
               help='DEPRECATED: Full class name for the Manager for '
                    'console proxy',
               deprecated_for_removal=True),
    cfg.StrOpt('consoleauth_manager',
               default='jacket.compute.consoleauth.manager.ConsoleAuthManager',
               help='DEPRECATED: Manager for console auth',
               deprecated_for_removal=True),
    cfg.StrOpt('cert_manager',
               default='jacket.compute.cert.manager.CertManager',
               help='DEPRECATED: Full class name for the Manager for cert',
               deprecated_for_removal=True),
    # NOTE(sdague): the network_manager has a bunch of different in
    # tree classes that are still legit options. In Newton we should
    # turn this into a selector.
    cfg.StrOpt('network_manager',
               default='jacket.compute.network.manager.VlanManager',
               help='Full class name for the Manager for network'),
    cfg.StrOpt('compute_scheduler_manager',
               default='jacket.compute.scheduler.manager.SchedulerManager',
               help='DEPRECATED: Full class name for the Manager for '
                    'scheduler',
               deprecated_for_removal=True),
    cfg.IntOpt('service_down_time',
               default=60,
               help='Maximum time since last check-in for up service'),
    cfg.IntOpt('periodic_interval',
               default=60,
               help='Interval, in seconds, between running periodic tasks'),
    cfg.StrOpt('osapi_volume_listen',
               default="0.0.0.0",
               help='IP address on which OpenStack Volume API listens'),
    cfg.PortOpt('osapi_volume_listen_port',
                default=8776,
                help='Port on which OpenStack Volume API listens'),
    cfg.IntOpt('osapi_volume_workers',
               help='Number of workers for OpenStack Volume API service. '
                    'The default is equal to the number of CPUs available.'),

    cfg.StrOpt('osapi_jacket_listen',
               default="0.0.0.0",
               help='IP address on which OpenStack jacket API listens'),
    cfg.PortOpt('osapi_jacket_listen_port',
                default=9774,
                help='Port on which OpenStack jacket API listens'),
    cfg.IntOpt('osapi_jacket_workers',
               help='Number of workers for OpenStack Jacket API service. '
                    'The default is equal to the number of CPUs available.'),
    cfg.IntOpt('jacket_controller_workers',
               help='Number of workers for OpenStack Jacket API service. '
                    'The default is equal to the number of CPUs available.'),
]

CONF = cfg.CONF
CONF.register_opts(service_opts)
CONF.import_opt('host', 'jacket.netconf')

if profiler_opts:
    profiler_opts.set_defaults(CONF)


def setup_profiler(binary, host):
    if (osprofiler_notifier is None or
                profiler is None or
                osprofiler_web is None or
                profiler_opts is None):
        LOG.debug('osprofiler is not present')
        return

    if CONF.profiler.enabled:
        _notifier = osprofiler_notifier.create(
            "Messaging", messaging, context.get_admin_context().to_dict(),
            rpc.TRANSPORT, "cinder", binary, host)
        osprofiler_notifier.set(_notifier)
        osprofiler_web.enable(CONF.profiler.hmac_keys)
        LOG.warning(
            _LW("OSProfiler is enabled.\nIt means that person who knows "
                "any of hmac_keys that are specified in "
                "/etc/cinder/cinder.conf can trace his requests. \n"
                "In real life only operator can read this file so there "
                "is no security issue. Note that even if person can "
                "trigger profiler, only admin user can retrieve trace "
                "information.\n"
                "To disable OSprofiler set in cinder.conf:\n"
                "[profiler]\nenabled=false"))
    else:
        osprofiler_web.disable()


def _create_service_ref(this_service, context):
    service = objects.Service(context)
    service.host = this_service.host
    service.binary = this_service.binary
    service.topic = this_service.topic
    service.report_count = 0
    service.availability_zone = CONF.default_availability_zone
    if hasattr(this_service.manager, 'RPC_API_VERSION'):
        service.rpc_current_version = this_service.manager.storage_manager.RPC_API_VERSION
    service.object_current_version = storage_objects_base.OBJ_VERSIONS.get_current()
    service.create()
    return service


def _update_service_ref(this_service, context):
    service = objects.Service.get_by_host_and_binary(context,
                                                     this_service.host,
                                                     this_service.binary)
    if not service:
        LOG.error(_LE('Unable to find a service record to update for '
                      '%(binary)s on %(host)s'),
                  {'binary': this_service.binary,
                   'host': this_service.host})
        return
    if service.version != service_obj.SERVICE_VERSION:
        LOG.info(_LI('Updating service version for %(binary)s on '
                     '%(host)s from %(old)i to %(new)i'),
                 {'binary': this_service.binary,
                  'host': this_service.host,
                  'old': service.version,
                  'new': service_obj.SERVICE_VERSION})
        service.version = service_obj.SERVICE_VERSION
        service.save()


class Service(service.Service):
    """Service object for binaries running on hosts.

    A service takes a manager and enables rpc by listening to queues based
    on topic. It also periodically runs tasks on the manager and reports
    its state to the database services table.
    """

    def __init__(self, host, binary, topic, manager, report_interval=None,
                 periodic_enable=None, periodic_fuzzy_delay=None,
                 periodic_interval_max=None, db_allowed=True,
                 *args, **kwargs):
        super(Service, self).__init__()
        self.host = host
        self.binary = binary
        self.topic = topic
        self.manager_class_name = manager
        self.servicegroup_api = servicegroup.API()
        manager_class = importutils.import_class(self.manager_class_name)
        self.manager = manager_class(host=self.host, *args, **kwargs)
        self.rpcserver = None
        self.report_interval = report_interval
        self.periodic_enable = periodic_enable
        self.periodic_fuzzy_delay = periodic_fuzzy_delay
        self.periodic_interval_max = periodic_interval_max
        self.saved_args, self.saved_kwargs = args, kwargs
        self.backdoor_port = None
        self.conductor_api = conductor.API(use_local=db_allowed)
        self.conductor_api.wait_until_ready(context.get_admin_context())

    def start(self):
        verstr = version.version_string_with_package()
        LOG.info(_LI('Starting %(topic)s node (version %(version)s)'),
                 {'topic': self.topic, 'version': verstr})
        self.basic_config_check()
        self.manager.init_host()
        self.model_disconnected = False
        ctxt = context.get_admin_context()
        self.service_ref = objects.Service.get_by_host_and_binary(
            ctxt, self.host, self.binary)
        if not self.service_ref:
            try:
                self.service_ref = _create_service_ref(self, ctxt)
            except (exception.ServiceTopicExists,
                    exception.ServiceBinaryExists):
                # NOTE(danms): If we race to create a record with a sibling
                # worker, don't fail here.
                self.service_ref = objects.Service.get_by_host_and_binary(
                    ctxt, self.host, self.binary)

        self.manager.pre_start_hook()

        if self.backdoor_port is not None:
            self.manager.backdoor_port = self.backdoor_port

        LOG.debug("Creating RPC server for service %s", self.topic)

        target = messaging.Target(topic=self.topic, server=self.host)

        endpoints = [
            self.manager,
            baserpc.BaseRPCAPI(self.manager.service_name, self.backdoor_port)
        ]
        endpoints.extend(self.manager.additional_endpoints)

        # serializer = objects_base.NovaObjectSerializer()
        serializer = objects_base.JacketObjectSerializer()

        self.rpcserver = rpc.get_server(target, endpoints, serializer)
        self.rpcserver.start()

        self.manager.post_start_hook()

        LOG.debug("Join ServiceGroup membership for this service %s",
                  self.topic)
        # Add service to the ServiceGroup membership group.
        self.servicegroup_api.join(self.host, self.topic, self)

        if self.periodic_enable:
            if self.periodic_fuzzy_delay:
                initial_delay = random.randint(0, self.periodic_fuzzy_delay)
            else:
                initial_delay = None

            self.tg.add_dynamic_timer(self.periodic_tasks,
                                      initial_delay=initial_delay,
                                      periodic_interval_max=
                                      self.periodic_interval_max)

    def __getattr__(self, key):
        manager = self.__dict__.get('manager', None)
        return getattr(manager, key)

    @classmethod
    def create(cls, host=None, binary=None, topic=None, manager=None,
               report_interval=None, periodic_enable=None,
               periodic_fuzzy_delay=None, periodic_interval_max=None,
               db_allowed=True):
        """Instantiates class and passes back application object.

        :param host: defaults to CONF.host
        :param binary: defaults to basename of executable
        :param topic: defaults to bin_name - 'compute-' part
        :param manager: defaults to CONF.<topic>_manager
        :param report_interval: defaults to CONF.report_interval
        :param periodic_enable: defaults to CONF.periodic_enable
        :param periodic_fuzzy_delay: defaults to CONF.periodic_fuzzy_delay
        :param periodic_interval_max: if set, the max time to wait between runs

        """
        if not host:
            host = CONF.host
        if not binary:
            binary = os.path.basename(sys.argv[0])
        if not topic:
            topic = binary.rpartition('jacket-')[2]
        if not manager:
            manager_cls = ('%s_manager' %
                           binary.rpartition('jacket-')[2])
            if binary == 'nova-compute':
                manager_cls = 'worker_manager'
            manager = CONF.get(manager_cls, None)

        if report_interval is None:
            report_interval = CONF.report_interval
        if periodic_enable is None:
            periodic_enable = CONF.periodic_enable
        if periodic_fuzzy_delay is None:
            periodic_fuzzy_delay = CONF.periodic_fuzzy_delay

        debugger.init()

        service_obj = cls(host, binary, topic, manager,
                          report_interval=report_interval,
                          periodic_enable=periodic_enable,
                          periodic_fuzzy_delay=periodic_fuzzy_delay,
                          periodic_interval_max=periodic_interval_max,
                          db_allowed=db_allowed)

        return service_obj

    def kill(self):
        """Destroy the service object in the datastore.

        NOTE: Although this method is not used anywhere else than tests, it is
        convenient to have it here, so the tests might easily and in clean way
        stop and remove the service_ref.

        """
        self.stop()
        try:
            self.service_ref.destroy()
        except exception.NotFound:
            LOG.warning(_LW('Service killed that has no database entry'))

    def stop(self):
        try:
            self.rpcserver.stop()
            self.rpcserver.wait()
        except Exception:
            pass

        try:
            self.manager.cleanup_host()
        except Exception:
            LOG.exception(_LE('Service error occurred during cleanup_host'))
            pass

        super(Service, self).stop()

    def periodic_tasks(self, raise_on_error=False):
        """Tasks to be run at a periodic interval."""
        ctxt = context.get_admin_context()
        return self.manager.periodic_tasks(ctxt, raise_on_error=raise_on_error)

    def basic_config_check(self):
        """Perform basic config checks before starting processing."""
        # Make sure the tempdir exists and is writable
        try:
            with utils.tempdir():
                pass
        except Exception as e:
            LOG.error(_LE('Temporary directory is invalid: %s'), e)
            sys.exit(1)

    def reset(self):
        self.manager.reset()


class WSGIService(service.Service):
    """Provides ability to launch API from a 'paste' configuration."""

    def __init__(self, name, loader=None, use_ssl=False, max_url_len=None):
        """Initialize, but do not start the WSGI server.

        :param name: The name of the WSGI server given to the loader.
        :param loader: Loads the WSGI application using the given name.
        :returns: None

        """
        self.name = name
        # NOTE(danms): Name can be metadata, os_compute, or ec2, per
        # compute.service's enabled_apis
        self.binary = 'jacket-%s' % name
        self.topic = None
        self.manager = self._get_manager()
        self.loader = loader or base_wsgi.Loader(name)
        self.app = self.loader.load_app(name)
        # inherit all compute_api worker counts from osapi_compute
        if name.startswith('openstack_compute_api'):
            wname = 'osapi_compute'
        else:
            wname = name
        self.host = getattr(CONF, '%s_listen' % name, "0.0.0.0")
        self.port = getattr(CONF, '%s_listen_port' % name, 0)
        self.workers = (getattr(CONF, '%s_workers' % wname, None) or
                        processutils.get_worker_count())
        if self.workers and self.workers < 1:
            worker_name = '%s_workers' % name
            msg = (_("%(worker_name)s value of %(workers)s is invalid, "
                     "must be greater than 0") %
                   {'worker_name': worker_name,
                    'workers': str(self.workers)})
            raise exception.InvalidInput(msg)
        self.use_ssl = use_ssl

        setup_profiler(name, self.host)

        self.server = base_wsgi.Server(name,
                                       self.app,
                                       host=self.host,
                                       port=self.port,
                                       use_ssl=self.use_ssl,
                                       max_url_len=max_url_len)
        # Pull back actual port used
        self.port = self.server.port
        self.backdoor_port = None

    def reset(self):
        """Reset server greenpool size to default.

        :returns: None

        """
        self.server.reset()

    def _get_manager(self):
        """Initialize a Manager object appropriate for this service.

        Use the service name to look up a Manager subclass from the
        configuration and initialize an instance. If no class name
        is configured, just return None.

        :returns: a Manager instance, or None.

        """
        fl = '%s_manager' % self.name
        if fl not in CONF:
            return None

        manager_class_name = CONF.get(fl, None)
        if not manager_class_name:
            return None

        manager_class = importutils.import_class(manager_class_name)
        return manager_class()

    def start(self):
        """Start serving this service using loaded configuration.

        Also, retrieve updated port number in case '0' was passed in, which
        indicates a random port should be used.

        :returns: None

        """
        ctxt = context.get_admin_context()
        service_ref = objects.Service.get_by_host_and_binary(ctxt, self.host,
                                                             self.binary)
        if not service_ref:
            try:
                service_ref = _create_service_ref(self, ctxt)
            except (exception.ServiceTopicExists,
                    exception.ServiceBinaryExists):
                # NOTE(danms): If we race to create a record wth a sibling,
                # don't fail here.
                service_ref = objects.Service.get_by_host_and_binary(
                    ctxt, self.host, self.binary)
        _update_service_ref(service_ref, ctxt)

        if self.manager:
            self.manager.init_host()
            self.manager.pre_start_hook()
            if self.backdoor_port is not None:
                self.manager.backdoor_port = self.backdoor_port
        self.server.start()
        if self.manager:
            self.manager.post_start_hook()

    def stop(self):
        """Stop serving this API.

        :returns: None

        """
        self.server.stop()

    def wait(self):
        """Wait for the service to stop serving this API.

        :returns: None

        """
        self.server.wait()


def process_launcher():
    return service.ProcessLauncher(CONF)


# NOTE(vish): the global launcher is to maintain the existing
#             functionality of calling service.serve +
#             service.wait
_launcher = None


def serve(server, workers=None):
    global _launcher
    if _launcher:
        raise RuntimeError(_('serve() can only be called once'))

    _launcher = service.launch(CONF, server, workers=workers)


def wait():
    _launcher.wait()
