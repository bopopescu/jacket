# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

import jacket.compute.conf
import jacket.compute.virt.configdrive
import jacket.compute.virt.disk.vfs.guestfs
import jacket.compute.virt.hyperv.eventhandler
import jacket.compute.virt.hyperv.pathutils
import jacket.compute.virt.hyperv.vif
import jacket.compute.virt.hyperv.vmops
import jacket.compute.virt.hyperv.volumeops
import jacket.compute.virt.imagecache
import jacket.compute.virt.libvirt.driver
import jacket.compute.virt.libvirt.imagebackend
import jacket.compute.virt.libvirt.imagecache
import jacket.compute.virt.libvirt.storage.lvm
import jacket.compute.virt.libvirt.utils
import jacket.compute.virt.libvirt.vif
import jacket.compute.virt.libvirt.volume.aoe
import jacket.compute.virt.libvirt.volume.glusterfs
import jacket.compute.virt.libvirt.volume.iscsi
import jacket.compute.virt.libvirt.volume.iser
import jacket.compute.virt.libvirt.volume.net
import jacket.compute.virt.libvirt.volume.nfs
import jacket.compute.virt.libvirt.volume.quobyte
import jacket.compute.virt.libvirt.volume.remotefs
import jacket.compute.virt.libvirt.volume.scality
import jacket.compute.virt.libvirt.volume.smbfs
import jacket.compute.virt.libvirt.volume.volume
import jacket.compute.virt.vmwareapi.driver
import jacket.compute.virt.vmwareapi.images
import jacket.compute.virt.vmwareapi.vif
import jacket.compute.virt.vmwareapi.vim_util
import jacket.compute.virt.vmwareapi.vm_util
import jacket.compute.virt.vmwareapi.vmops
import jacket.compute.virt.xenapi.agent
import jacket.compute.virt.xenapi.client.session
import jacket.compute.virt.xenapi.driver
import jacket.compute.virt.xenapi.image.bittorrent
import jacket.compute.virt.xenapi.pool
import jacket.compute.virt.xenapi.vif
import jacket.compute.virt.xenapi.vm_utils
import jacket.compute.virt.xenapi.vmops
import jacket.compute.virt.xenapi.volume_utils


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             jacket.compute.virt.configdrive.configdrive_opts,
             jacket.compute.virt.imagecache.imagecache_opts,
         )),
        ('guestfs', jacket.compute.virt.disk.vfs.guestfs.guestfs_opts),
        ('hyperv',
         itertools.chain(
             jacket.compute.virt.hyperv.pathutils.hyperv_opts,
             jacket.compute.virt.hyperv.vif.hyperv_opts,
             jacket.compute.virt.hyperv.vmops.hyperv_opts,
             jacket.compute.virt.hyperv.volumeops.hyper_volumeops_opts,
             jacket.compute.virt.hyperv.eventhandler.hyperv_opts
         )),
        ('libvirt',
         itertools.chain(
             jacket.compute.virt.libvirt.driver.libvirt_opts,
             jacket.compute.virt.libvirt.imagebackend.__imagebackend_opts,
             jacket.compute.virt.libvirt.imagecache.imagecache_opts,
             jacket.compute.virt.libvirt.storage.lvm.lvm_opts,
             jacket.compute.virt.libvirt.utils.libvirt_opts,
             jacket.compute.virt.libvirt.vif.libvirt_vif_opts,
             jacket.compute.virt.libvirt.volume.volume.volume_opts,
             jacket.compute.virt.libvirt.volume.aoe.volume_opts,
             jacket.compute.virt.libvirt.volume.glusterfs.volume_opts,
             jacket.compute.virt.libvirt.volume.iscsi.volume_opts,
             jacket.compute.virt.libvirt.volume.iser.volume_opts,
             jacket.compute.virt.libvirt.volume.net.volume_opts,
             jacket.compute.virt.libvirt.volume.nfs.volume_opts,
             jacket.compute.virt.libvirt.volume.quobyte.volume_opts,
             jacket.compute.virt.libvirt.volume.remotefs.libvirt_opts,
             jacket.compute.virt.libvirt.volume.scality.volume_opts,
             jacket.compute.virt.libvirt.volume.smbfs.volume_opts,
         )),
        ('vmware',
         itertools.chain(
             [jacket.compute.virt.vmwareapi.vim_util.vmware_opts],
             jacket.compute.virt.vmwareapi.driver.spbm_opts,
             jacket.compute.virt.vmwareapi.driver.vmwareapi_opts,
             jacket.compute.virt.vmwareapi.vif.vmwareapi_vif_opts,
             jacket.compute.virt.vmwareapi.vm_util.vmware_utils_opts,
             jacket.compute.virt.vmwareapi.vmops.vmops_opts,
         )),
        ('xenserver',
         itertools.chain(
             [jacket.compute.virt.xenapi.vif.xenapi_ovs_integration_bridge_opt],
             jacket.compute.virt.xenapi.agent.xenapi_agent_opts,
             jacket.compute.virt.xenapi.client.session.xenapi_session_opts,
             jacket.compute.virt.xenapi.driver.xenapi_opts,
             jacket.compute.virt.xenapi.image.bittorrent.xenapi_torrent_opts,
             jacket.compute.virt.xenapi.pool.xenapi_pool_opts,
             jacket.compute.virt.xenapi.vm_utils.xenapi_vm_utils_opts,
             jacket.compute.virt.xenapi.vmops.xenapi_vmops_opts,
             jacket.compute.virt.xenapi.volume_utils.xenapi_volume_utils_opts,
         )),
    ]
