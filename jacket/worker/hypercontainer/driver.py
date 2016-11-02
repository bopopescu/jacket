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

from retrying import retry

from oslo_log import log as logging

from jacket import conf
from jacket.i18n import _LI, _LW
from jacket.worker.hypercontainer.wormhole_business import WormHoleBusiness
from jacket.worker.hypercontainer.wormhole_business import RetryException
from wormholeclient.client import Client

LOG = logging.getLogger(__name__)

CONF = conf.CONF


def retry_if_ignore_exe(exception):
    return isinstance(exception, RetryException)


def retry_if_result_is_false(result):
    return result is False


class JacketHyperContainerDriver():
    def _create_wormhole(self, instance):
        # LOG.debug('instance: %s' % instance)
        port = CONF.hybrid_cloud_agent_opts.hybrid_service_port
        ips = self._get_private_ips(instance)
        # LOG.debug('luorui debug ips %s' % ips)
        clients = self._get_clients(ips, port)
        wormhole = WormHoleBusiness(clients)
        return wormhole

    def stop_container(self, instance):

        LOG.debug('start to stop container')
        wormhole = self._create_wormhole(instance)

        try:
            version = wormhole.get_version()
        except Exception:
            LOG.debug('hyper service is not online, stop base vm directlly.')
            version = None

        if version:
            wormhole.stop_container()

        LOG.info(_LI('in Server: %s, stop container success!') % (
            instance.display_name))

    def start_container(self, instance, network_info, block_device_info):

        wormhole = self._create_wormhole(instance)
        LOG.debug('start to start container')

        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online, no need to start container')
            version = None

        if version:
            wormhole.start_container(network_info,
                                     block_device_info)

        LOG.info(_LI('in Server: %s, start container success!') % (
            instance.display_name))

    def restart_container(self, instance, network_info, block_device_info):

        wormhole = self._create_wormhole(instance)
        LOG.debug('start to restart container')

        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error(
                'hyper service is not online, no need to restart container')
            version = None

        if version:
            wormhole.restart_container(network_info,
                                       block_device_info)

        LOG.info(_LI('in Server: %s, restart container success!') % (
            instance.display_name))

    def pause(self, instance):

        LOG.debug('start to pause instance: %s' % instance)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.pause()

        LOG.info(_LI('in Server: %s, pause container success!') % (
            instance.display_name))

    def unpause(self, instance):

        LOG.debug('start to unpause instance: %s' % instance)
        wormhole = self._create_wormhole(instance)

        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.unpause()

        LOG.info(_LI('in Server: %s, unpause container success!') % (
            instance.display_name))

    def attach_interface(self, instance, vif):

        LOG.debug('start to attach interface: %s' % vif)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.attach_interface(vif)

        LOG.info(_LI('in Server: %s, container attach interface success!') % (
            instance.display_name))

    def detach_interface(self, instance, vif):
        LOG.debug('start to detach interface: %s' % vif)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.detach_interface(vif)

        LOG.info(_LI('in Server: %s, container detach interface success!') % (
            instance.display_name))

    def attach_volume(self, instance, volume_id, device, mount_device):
        LOG.debug('start to attach volume: %s' % volume_id)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.attach_volume(volume_id, device,
                                   mount_device)
        LOG.info(_LI('Attach Volume success!'), instance=instance)

    def detach_volume(self, instance, volume_id):
        LOG.debug('start to detach volume: %s' % volume_id)
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        if version:
            wormhole.detach_volume(volume_id)
        LOG.info(_LI('Detach Volume success!'))

    def list_volumes(self, instance):
        LOG.debug('List volumes')
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        list_result = []
        if version:
            volumes = wormhole.list_volume()
            list_result = volumes.get("devices", [])
        LOG.info(_LI('List Volume result is: %s') % list_result)
        return list_result

    def status(self, instance):
        LOG.debug('start to get container status')
        wormhole = self._create_wormhole(instance)
        try:
            version = wormhole.get_version()
        except Exception:
            LOG.error('hyper service is not online')
            version = None

        status_result = None
        if version:
            status_result = wormhole.status()
        LOG.info(_LI('Get container status result is: %s') % status_result)
        return status_result

    @retry(stop_max_attempt_number=300,
           wait_fixed=2000,
           retry_on_result=retry_if_result_is_false,
           retry_on_exception=retry_if_ignore_exe)
    def wait_container_in_specified_status(self, instance, specified_status):
        wormhole = self._create_wormhole(instance)
        try:
            status_result = wormhole.status()
            if status_result is not None and \
                            status_result['status']['code'] == specified_status:
                LOG.debug("wait_container_in_specified_status %s success!",
                          specified_status, instance=instance)
                return True
            else:
                LOG.debug("current status = %s, expect status(%s)",
                          status_result, specified_status, instance=instance)
                return False
        except RetryException:
            LOG.warning(_LW('hyper service is not online'), instance=instance)
            return False

    def _get_clients(self, ips, port):
        clients = []
        for ip in ips:
            clients.append(Client(ip, port, timeout=10))

        return clients

    def _get_private_ips(self, instance):
        instance_ips = instance.system_metadata.get('instance_ips')
        ips = instance_ips.split(',')
        return ips
