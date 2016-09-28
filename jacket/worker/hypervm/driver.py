__author__ = 'luorui'


from jacket.worker.hypervm.wormhole_business import *
from jacket.compute.virt.driver import CONF

from wormholeclient.client import Client



LOG = logging.getLogger(__name__)


hybrid_cloud_agent_opts = [
    cfg.StrOpt('hybrid_service_port',
               default='7127',
               help='The route gw of the provider network.'),
    ]


CONF = cfg.CONF
CONF.register_opts(hybrid_cloud_agent_opts, 'hybrid_cloud_agent_opts')


class JacketHypervmDriver():

    def _create_wormhole(self, instance):
        #LOG.debug('instance: %s' % instance)
        port = CONF.hybrid_cloud_agent_opts.hybrid_service_port
        ips = self._get_private_ips(instance)
        #LOG.debug('luorui debug ips %s' % ips)
        clients = self._get_clients(ips, port)
        wormhole = WormHoleBusiness(clients)
        return wormhole

    def stop_container(self, instance):
        LOG.debug('start to stop container')
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.debug('hyper service is not online, stop base vm directlly.')
            version = None
        if version:
            stop_result = wormhole.stop_container()
        LOG.info('Stop Server: %s, result is: %s' % (instance.display_name, stop_result))

    def start_container(self, instance, network_info, block_device_info):
        wormhole = self._create_wormhole(instance)
        LOG.debug('start to start container')
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online, no need to start container')
            version = None

        if version:
            start_result = wormhole.start_container(network_info, block_device_info)

        LOG.info('Start Server: %s, result is: %s' % (instance.display_name, start_result))

    def restart_container(self, instance, network_info, block_device_info):
        wormhole = self._create_wormhole(instance)
        LOG.debug('start to restart container')
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online, no need to restart container')
            version = None

        if version:
            restart_result = wormhole.restart_container(network_info, block_device_info)

        LOG.info('Restart Server: %s, result is: %s' % (instance.display_name, restart_result))

    def pause(self, instance):
        LOG.debug('start to pause instance: %s' % instance)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            pause_result = wormhole.pause()
        LOG.info('Pause Server: %s, result is: %s' % (instance.display_name, pause_result))

    def unpause(self, instance):
        LOG.debug('start to unpause instance: %s' % instance)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            unpause_result = wormhole.unpause()
        LOG.info('Unpause Server: %s, result is: %s' % (instance.display_name, unpause_result))

    def attach_interface(self, instance, vif):
        LOG.debug('start to attach interface: %s' % vif)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            attach_result = wormhole.attach_interface(vif)
        LOG.info('Attach interface result is: %s' % attach_result)

    def detach_interface(self, instance, vif):
        LOG.debug('start to detach interface: %s' % vif)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            detach_result = wormhole.detach_interface(vif)
        LOG.info('Detach interface result is: %s' % detach_result)

    def attach_volume(self, instance, volume_id, device, mount_device):
        LOG.debug('start to attach volume: %s' % volume_id)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            attach_result = wormhole.attach_volume(volume_id, device, mount_device)
        LOG.info('Attach Volume result is: %s' % attach_result)

    def detach_volume(self, instance, volume_id):
        LOG.debug('start to detach volume: %s' % volume_id)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            detach_result = wormhole.detach_volume(volume_id)
        LOG.info('Detach Volume result is: %s' % detach_result)

    def list_volumes(self, instance):
        LOG.debug('List volumes')
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            list_result = wormhole.list_volume()
        LOG.info('List Volume result is: %s' % list_result)
        return list_result

    def status(self, instance):
        LOG.debug('start to get container status')
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception, e:
            LOG.error('hyper service is not online')
            version = None
        if version:
            status_result = wormhole.status()
        LOG.info('Get container status result is: %s' % status_result)
        return status_result

    @RetryDecorator(max_retry_count=50, inc_sleep_time=5, max_sleep_time=30, exceptions=(RetryException))
    def wait_container_in_specified_status(self, instance, specified_status):
        LOG.debug('Wait container in specified status')
        wormhole = self._create_wormhole(instance)
        try:
            status_result = wormhole.status()
            if status_result['status']['code'] == specified_status:
                return
        except Exception, e:
            LOG.warning('hyper service is not online')
        LOG.warning('hyper service is not in specified status')
        raise RetryException

    def _get_clients(self, ips, port):
        clients = []
        for ip in ips:
            clients.append(Client(ip, port, timeout=10))

        return clients

    def _get_private_ips(self, instance):
        instance_ips = instance.system_metadata.get('instance_ips')
        ips = instance_ips.split(',')
        return ips

