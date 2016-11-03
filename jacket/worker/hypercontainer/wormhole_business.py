__author__ = 'Administrator'

import time
import traceback

from functools import wraps
from wormholeclient.client import Client
from wormholeclient import constants as wormhole_constants

from jacket.compute.exception import *

from oslo_log import log as logging


LOG = logging.getLogger(__name__)


class RetryDecorator(object):
    """Decorator for retrying a function upon suggested exceptions.

    The decorated function is retried for the given number of times, and the
    sleep time between the retries is incremented until max sleep time is
    reached. If the max retry count is set to -1, then the decorated function
    is invoked indefinitely until an exception is thrown, and the caught
    exception is not in the list of suggested exceptions.
    """

    def __init__(self, max_retry_count=-1, inc_sleep_time=5,
                 max_sleep_time=60, exceptions=()):
        """Configure the retry object using the input params.

        :param max_retry_count: maximum number of times the given function must
                                be retried when one of the input 'exceptions'
                                is caught. When set to -1, it will be retried
                                indefinitely until an exception is thrown
                                and the caught exception is not in param
                                exceptions.
        :param inc_sleep_time: incremental time in seconds for sleep time
                               between retries
        :param max_sleep_time: max sleep time in seconds beyond which the sleep
                               time will not be incremented using param
                               inc_sleep_time. On reaching this threshold,
                               max_sleep_time will be used as the sleep time.
        :param exceptions: suggested exceptions for which the function must be
                           retried
        """
        self._max_retry_count = max_retry_count
        self._inc_sleep_time = inc_sleep_time
        self._max_sleep_time = max_sleep_time
        self._exceptions = exceptions
        self._retry_count = 0
        self._sleep_time = 0

    def __call__(self, f):
            @wraps(f)
            def f_retry(*args, **kwargs):
                max_retries, mdelay = self._max_retry_count, self._inc_sleep_time
                while max_retries > 1:
                    try:
                        return f(*args, **kwargs)
                    except self._exceptions as e:
                        LOG.error('retry times: %s, exception: %s' %
                                  (str(self._max_retry_count - max_retries), traceback.format_exc(e)))
                        time.sleep(mdelay)
                        max_retries -= 1
                        if mdelay >= self._max_sleep_time:
                            mdelay = self._max_sleep_time
                if max_retries == 1:
                    msg = 'func: %s, retry times: %s, failed' % (f.__name__, str(self._max_retry_count))
                    LOG.error(msg)
                return f(*args, **kwargs)

            return f_retry

class WormHoleBusiness(object):

    def __init__(self, clients):
        self.clients = clients

    def get_version(self):
        version = self._run_function_of_clients('get_version')
        return version

    def restart_container(self, network_info, block_device_info):
        return self._run_function_of_clients('restart_container', network_info=network_info,
                                      block_device_info=block_device_info)

    def start_container(self, network_info, block_device_info):
        return self._run_function_of_clients('start_container', network_info=network_info,
                                      block_device_info=block_device_info)

    def restart_container(self, network_info, block_device_info):
        return self._run_function_of_clients('restart_container', network_info=network_info,
                                      block_device_info=block_device_info)

    def stop_container(self):
        return self._run_function_of_clients('stop_container')

    def create_container(self, name, image_uuid, injected_files, admin_password, network_info,
                                                                      block_device_info):
        return self._run_function_of_clients('create_container', image_name=name,
                                             image_id=image_uuid, root_volume_id=None,
                                             network_info=network_info, block_device_info=block_device_info,
                                             inject_files=injected_files, admin_password=admin_password,
                                             timeout=10)

    def pause(self):
        return self._run_function_of_clients('pause_container')

    def unpause(self):
        return self._run_function_of_clients('unpause_container')

    def inject_file(self, dst_path, src_path=None, file_data=None, timeout=10):
        return self._run_function_of_clients('inject_file', dst_path=dst_path, src_path=src_path,
                                             file_data=file_data, timeout=timeout)

    def list_volume(self):
        return self._run_function_of_clients('list_volume')

    def attach_volume(self, volume_id, device, mount_device, timeout=10):
        return self._run_function_of_clients('attach_volume', volume_id=volume_id,
                                             device=device, mount_device=mount_device, timeout=timeout)

    def detach_volume(self, volume_id, timeout=10):
        return self._run_function_of_clients('detach_volume', volume_id=volume_id, timeout=timeout)

    def attach_interface(self, vif, timeout=10):
        return self._run_function_of_clients('attach_interface', vif=vif, timeout=timeout)

    def detach_interface(self, vif, timeout=10):
        return self._run_function_of_clients('detach_interface', vif=vif, timeout=timeout)

    def create_image(self, image_name, image_id, timeout=10):
        return self._run_function_of_clients('create_image', image_name=image_name,
                                             image_id=image_id, timeout=timeout)

    def image_info(self, image_name, image_id):
        return self._run_function_of_clients('image_info', image_name=image_name, image_id=image_id)

    def query_task(self, task, timeout=10):
        return self._run_function_of_clients('query_task', task=task, timeout=timeout)

    def status(self):
        return self._run_function_of_clients('status')

    @RetryDecorator(max_retry_count=60, inc_sleep_time=5, max_sleep_time=60,
                    exceptions=(RetryException))
    def _run_function_of_clients(self, function_name, *args, **kwargs):
        result = None
        tmp_except = Exception('tmp exception when doing function: %s' % function_name)

        for client in self.clients:
            func = getattr(client, function_name)
            if func:
                try:
                    result = func(*args, **kwargs)
                    #LOG.debug('Finish to execute %s' % function_name)
                    self.clients = []
                    self.clients.append(client)
                    break
                except Exception, e:
                    tmp_except = e
                    continue
            else:
                raise Exception('There is not such function >%s< in wormhole client.' % function_name)

        if not result:
            #LOG.debug('exception is: %s' % traceback.format_exc(tmp_except))
            raise RetryException(error_info=tmp_except.message)

        return result

    @RetryDecorator(max_retry_count=50, inc_sleep_time=5, max_sleep_time=60,
                    exceptions=(RetryException))
    def wait_for_task_finish(self, task):
        task_finish = False
        if task['code'] == wormhole_constants.TASK_SUCCESS:
            return True
        current_task = self.query_task(task)
        task_code = current_task['code']

        if wormhole_constants.TASK_DOING == task_code:
            LOG.debug('task is DOING, status: %s' % task_code)
            raise RetryException(error_info='task status is: %s' % task_code)
        elif wormhole_constants.TASK_ERROR == task_code:
            LOG.debug('task is ERROR, status: %s' % task_code)
            raise Exception('task error, task status is: %s' % task_code)
        elif wormhole_constants.TASK_SUCCESS == task_code:
            LOG.debug('task is SUCCESS, status: %s' % task_code)
            task_finish = True
        else:
            raise Exception('UNKNOW ERROR, task status: %s' % task_code)

        LOG.debug('task: %s is finished' % task )

        return task_finish


if __name__ == '__main__':
    clients = []
    clients.append(Client('10.16.2.77', 7127))
    wormhole = WormHoleBusiness(clients)
    import pdb;pdb.set_trace()
    try:
       docker_version = wormhole.get_version()
    except Exception, e:
        error_info = 'docker server is not up, create docker app failed, exception: %s' % \
                     traceback.format_exc(e)
        raise Exception(error_info)
