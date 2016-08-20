# Copyright 2013 Cloudbase Solutions Srl
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

import os

from os_win.utils import pathutils
from oslo_config import cfg

from jacket.compute import exception
from jacket.i18n import _
from jacket.compute.virt.hyperv import constants

hyperv_opts = [
    cfg.StrOpt('instances_path_share',
               default="",
               help='The name of a Windows share name mapped to the '
                    '"instances_path" dir and used by the resize feature '
                    'to copy files to the target host. If left blank, an '
                    'administrative share will be used, looking for the same '
                    '"instances_path" used locally'),
]

CONF = cfg.CONF
CONF.register_opts(hyperv_opts, 'hyperv')
CONF.import_opt('instances_path', 'jacket.compute.cloud.manager')

ERROR_INVALID_NAME = 123

# NOTE(claudiub): part of the pre-existing PathUtils is compute-specific and
# it does not belong in the os-win library. In order to ensure the same
# functionality with the least amount of changes necessary, adding as a mixin
# the os_win.pathutils.PathUtils class into this PathUtils.


class PathUtils(pathutils.PathUtils):

    def get_instances_dir(self, remote_server=None):
        local_instance_path = os.path.normpath(CONF.instances_path)

        if remote_server:
            if CONF.hyperv.instances_path_share:
                path = CONF.hyperv.instances_path_share
            else:
                # Use an administrative share
                path = local_instance_path.replace(':', '$')
            return ('\\\\%(remote_server)s\\%(path)s' %
                {'remote_server': remote_server, 'path': path})
        else:
            return local_instance_path

    def _get_instances_sub_dir(self, dir_name, remote_server=None,
                               create_dir=True, remove_dir=False):
        instances_path = self.get_instances_dir(remote_server)
        path = os.path.join(instances_path, dir_name)
        try:
            if remove_dir:
                self.check_remove_dir(path)
            if create_dir:
                self.check_create_dir(path)
            return path
        except WindowsError as ex:
            if ex.winerror == ERROR_INVALID_NAME:
                raise exception.AdminRequired(_(
                    "Cannot access \"%(instances_path)s\", make sure the "
                    "path exists and that you have the proper permissions. "
                    "In particular Nova-Compute must not be executed with the "
                    "builtin SYSTEM account or other accounts unable to "
                    "authenticate on a remote host.") %
                    {'instances_path': instances_path})
            raise

    def get_instance_migr_revert_dir(self, instance_name, create_dir=False,
                                     remove_dir=False):
        dir_name = '%s_revert' % instance_name
        return self._get_instances_sub_dir(dir_name, None, create_dir,
                                           remove_dir)

    def get_instance_dir(self, instance_name, remote_server=None,
                         create_dir=True, remove_dir=False):
        return self._get_instances_sub_dir(instance_name, remote_server,
                                           create_dir, remove_dir)

    def _lookup_vhd_path(self, instance_name, vhd_path_func):
        vhd_path = None
        for format_ext in ['vhd', 'vhdx']:
            test_path = vhd_path_func(instance_name, format_ext)
            if self.exists(test_path):
                vhd_path = test_path
                break
        return vhd_path

    def lookup_root_vhd_path(self, instance_name):
        return self._lookup_vhd_path(instance_name, self.get_root_vhd_path)

    def lookup_configdrive_path(self, instance_name):
        configdrive_path = None
        for format_ext in constants.DISK_FORMAT_MAP:
            test_path = self.get_configdrive_path(instance_name, format_ext)
            if self.exists(test_path):
                configdrive_path = test_path
                break
        return configdrive_path

    def lookup_ephemeral_vhd_path(self, instance_name):
        return self._lookup_vhd_path(instance_name,
                                     self.get_ephemeral_vhd_path)

    def get_root_vhd_path(self, instance_name, format_ext):
        instance_path = self.get_instance_dir(instance_name)
        return os.path.join(instance_path, 'root.' + format_ext.lower())

    def get_configdrive_path(self, instance_name, format_ext,
                             remote_server=None):
        instance_path = self.get_instance_dir(instance_name, remote_server)
        return os.path.join(instance_path, 'configdrive.' + format_ext.lower())

    def get_ephemeral_vhd_path(self, instance_name, format_ext):
        instance_path = self.get_instance_dir(instance_name)
        return os.path.join(instance_path, 'ephemeral.' + format_ext.lower())

    def get_base_vhd_dir(self):
        return self._get_instances_sub_dir('_base')

    def get_export_dir(self, instance_name):
        dir_name = os.path.join('export', instance_name)
        return self._get_instances_sub_dir(dir_name, create_dir=True,
                                           remove_dir=True)

    def get_vm_console_log_paths(self, vm_name, remote_server=None):
        instance_dir = self.get_instance_dir(vm_name,
                                             remote_server)
        console_log_path = os.path.join(instance_dir, 'console.log')
        return console_log_path, console_log_path + '.1'
