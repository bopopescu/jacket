
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import itertools

from jacket.api.storage import common as cinder_api_common
from jacket.api.middleware import auth as cinder_api_middleware_auth
from jacket.api.middleware import sizelimit as cinder_api_middleware_sizelimit
from jacket.api.storage.views import versions as cinder_api_views_versions
from jacket.storage.backup import api as cinder_backup_api
from jacket.storage.backup import chunkeddriver as cinder_backup_chunkeddriver
from jacket.storage.backup import driver as cinder_backup_driver
from jacket.storage.backup.drivers import ceph as cinder_backup_drivers_ceph
from jacket.storage.backup.drivers import glusterfs as cinder_backup_drivers_glusterfs
from jacket.storage.backup.drivers import google as cinder_backup_drivers_google
from jacket.storage.backup.drivers import nfs as cinder_backup_drivers_nfs
from jacket.storage.backup.drivers import posix as cinder_backup_drivers_posix
from jacket.storage.backup.drivers import swift as cinder_backup_drivers_swift
from jacket.storage.backup.drivers import tsm as cinder_backup_drivers_tsm
from jacket.storage.backup import manager as cinder_backup_manager
from jacket.cmd.storage import all as cinder_cmd_all
from jacket.cmd.storage import volume as cinder_cmd_volume
from jacket.common.storage import config as cinder_common_config
import jacket.storage.compute
from jacket.storage.compute import nova as cinder_compute_nova
from jacket.storage import context as cinder_context
from jacket.storage import coordination as cinder_coordination
from jacket.db import api as cinder_db_api
from jacket.db import base as cinder_db_base
from jacket.storage import exception as cinder_exception
from jacket.storage.image import glance as cinder_image_glance
from jacket.storage.image import image_utils as cinder_image_imageutils
import jacket.storage.keymgr
from jacket.storage.keymgr import conf_key_mgr as cinder_keymgr_confkeymgr
from jacket.storage.keymgr import key_mgr as cinder_keymgr_keymgr
from jacket.storage import quota as cinder_quota
from jacket.storage.scheduler import driver as cinder_scheduler_driver
from jacket.storage.scheduler import host_manager as cinder_scheduler_hostmanager
from jacket.storage.scheduler import manager as cinder_scheduler_manager
from jacket.storage.scheduler import scheduler_options as \
    cinder_scheduler_scheduleroptions
from jacket.storage.scheduler.weights import capacity as \
    cinder_scheduler_weights_capacity
from jacket.storage.scheduler.weights import volume_number as \
    cinder_scheduler_weights_volumenumber
# from jacket import service as cinder_service
from jacket.storage import ssh_utils as cinder_sshutils
from jacket.storage.transfer import api as cinder_transfer_api
from jacket.storage.volume import api as cinder_volume_api
from jacket.storage.volume import driver as cinder_volume_driver
from jacket.storage.volume.drivers import block_device as \
    cinder_volume_drivers_blockdevice
from jacket.storage.volume.drivers import blockbridge as \
    cinder_volume_drivers_blockbridge
from jacket.storage.volume.drivers.cloudbyte import options as \
    cinder_volume_drivers_cloudbyte_options
from jacket.storage.volume.drivers import coho as cinder_volume_drivers_coho
from jacket.storage.volume.drivers import datera as cinder_volume_drivers_datera
from jacket.storage.volume.drivers.dell import dell_storagecenter_common as \
    cinder_volume_drivers_dell_dellstoragecentercommon
from jacket.storage.volume.drivers.disco import disco as \
    cinder_volume_drivers_disco_disco
from jacket.storage.volume.drivers.dothill import dothill_common as \
    cinder_volume_drivers_dothill_dothillcommon
from jacket.storage.volume.drivers import drbdmanagedrv as \
    cinder_volume_drivers_drbdmanagedrv
from jacket.storage.volume.drivers.emc import emc_vmax_common as \
    cinder_volume_drivers_emc_emcvmaxcommon
from jacket.storage.volume.drivers.emc import emc_vnx_cli as \
    cinder_volume_drivers_emc_emcvnxcli
from jacket.storage.volume.drivers.emc import scaleio as \
    cinder_volume_drivers_emc_scaleio
from jacket.storage.volume.drivers.emc import xtremio as \
    cinder_volume_drivers_emc_xtremio
from jacket.storage.volume.drivers import eqlx as cinder_volume_drivers_eqlx
from jacket.storage.volume.drivers.fujitsu import eternus_dx_common as \
    cinder_volume_drivers_fujitsu_eternusdxcommon
from jacket.storage.volume.drivers import glusterfs as cinder_volume_drivers_glusterfs
from jacket.storage.volume.drivers import hgst as cinder_volume_drivers_hgst
from jacket.storage.volume.drivers.hitachi import hbsd_common as \
    cinder_volume_drivers_hitachi_hbsdcommon
from jacket.storage.volume.drivers.hitachi import hbsd_fc as \
    cinder_volume_drivers_hitachi_hbsdfc
from jacket.storage.volume.drivers.hitachi import hbsd_horcm as \
    cinder_volume_drivers_hitachi_hbsdhorcm
from jacket.storage.volume.drivers.hitachi import hbsd_iscsi as \
    cinder_volume_drivers_hitachi_hbsdiscsi
from jacket.storage.volume.drivers.hitachi import hnas_iscsi as \
    cinder_volume_drivers_hitachi_hnasiscsi
from jacket.storage.volume.drivers.hitachi import hnas_nfs as \
    cinder_volume_drivers_hitachi_hnasnfs
from jacket.storage.volume.drivers.hpe import hpe_3par_common as \
    cinder_volume_drivers_hpe_hpe3parcommon
from jacket.storage.volume.drivers.hpe import hpe_lefthand_iscsi as \
    cinder_volume_drivers_hpe_hpelefthandiscsi
from jacket.storage.volume.drivers.hpe import hpe_xp_opts as \
    cinder_volume_drivers_hpe_hpexpopts
from jacket.storage.volume.drivers.huawei import huawei_driver as \
    cinder_volume_drivers_huawei_huaweidriver
from jacket.storage.volume.drivers.ibm import flashsystem_common as \
    cinder_volume_drivers_ibm_flashsystemcommon
from jacket.storage.volume.drivers.ibm import flashsystem_fc as \
    cinder_volume_drivers_ibm_flashsystemfc
from jacket.storage.volume.drivers.ibm import flashsystem_iscsi as \
    cinder_volume_drivers_ibm_flashsystemiscsi
from jacket.storage.volume.drivers.ibm import gpfs as cinder_volume_drivers_ibm_gpfs
from jacket.storage.volume.drivers.ibm.storwize_svc import storwize_svc_common as \
    cinder_volume_drivers_ibm_storwize_svc_storwizesvccommon
from jacket.storage.volume.drivers.ibm.storwize_svc import storwize_svc_fc as \
    cinder_volume_drivers_ibm_storwize_svc_storwizesvcfc
from jacket.storage.volume.drivers.ibm.storwize_svc import storwize_svc_iscsi as \
    cinder_volume_drivers_ibm_storwize_svc_storwizesvciscsi
from jacket.storage.volume.drivers.ibm import xiv_ds8k as \
    cinder_volume_drivers_ibm_xivds8k
from jacket.storage.volume.drivers.infortrend.eonstor_ds_cli import common_cli as \
    cinder_volume_drivers_infortrend_eonstor_ds_cli_commoncli
from jacket.storage.volume.drivers.lenovo import lenovo_common as \
    cinder_volume_drivers_lenovo_lenovocommon
from jacket.storage.volume.drivers import lvm as cinder_volume_drivers_lvm
from jacket.storage.volume.drivers.netapp import options as \
    cinder_volume_drivers_netapp_options
from jacket.storage.volume.drivers.nexenta import options as \
    cinder_volume_drivers_nexenta_options
from jacket.storage.volume.drivers import nfs as cinder_volume_drivers_nfs
from jacket.storage.volume.drivers import nimble as cinder_volume_drivers_nimble
from jacket.storage.volume.drivers.prophetstor import options as \
    cinder_volume_drivers_prophetstor_options
from jacket.storage.volume.drivers import pure as cinder_volume_drivers_pure
from jacket.storage.volume.drivers import quobyte as cinder_volume_drivers_quobyte
from jacket.storage.volume.drivers import rbd as cinder_volume_drivers_rbd
from jacket.storage.volume.drivers import remotefs as cinder_volume_drivers_remotefs
from jacket.storage.volume.drivers.san.hp import hpmsa_common as \
    cinder_volume_drivers_san_hp_hpmsacommon
from jacket.storage.volume.drivers.san import san as cinder_volume_drivers_san_san
from jacket.storage.volume.drivers import scality as cinder_volume_drivers_scality
from jacket.storage.volume.drivers import sheepdog as cinder_volume_drivers_sheepdog
from jacket.storage.volume.drivers import smbfs as cinder_volume_drivers_smbfs
from jacket.storage.volume.drivers import solidfire as cinder_volume_drivers_solidfire
from jacket.storage.volume.drivers import tegile as cinder_volume_drivers_tegile
from jacket.storage.volume.drivers import tintri as cinder_volume_drivers_tintri
from jacket.storage.volume.drivers.violin import v7000_common as \
    cinder_volume_drivers_violin_v7000common
from jacket.storage.volume.drivers.vmware import vmdk as \
    cinder_volume_drivers_vmware_vmdk
from jacket.storage.volume.drivers import vzstorage as cinder_volume_drivers_vzstorage
from jacket.storage.volume.drivers.windows import windows as \
    cinder_volume_drivers_windows_windows
from jacket.storage.volume.drivers import xio as cinder_volume_drivers_xio
from jacket.storage.volume.drivers.zfssa import zfssaiscsi as \
    cinder_volume_drivers_zfssa_zfssaiscsi
from jacket.storage.volume.drivers.zfssa import zfssanfs as \
    cinder_volume_drivers_zfssa_zfssanfs
from jacket.storage.volume import manager as cinder_volume_manager
from jacket.wsgi.storage import eventlet_server as cinder_wsgi_eventletserver
from jacket.storage.zonemanager.drivers.brocade import brcd_fabric_opts as \
    cinder_zonemanager_drivers_brocade_brcdfabricopts
from jacket.storage.zonemanager.drivers.brocade import brcd_fc_zone_driver as \
    cinder_zonemanager_drivers_brocade_brcdfczonedriver
from jacket.storage.zonemanager.drivers.cisco import cisco_fabric_opts as \
    cinder_zonemanager_drivers_cisco_ciscofabricopts
from jacket.storage.zonemanager.drivers.cisco import cisco_fc_zone_driver as \
    cinder_zonemanager_drivers_cisco_ciscofczonedriver
from jacket.storage.zonemanager import fc_zone_manager as \
    cinder_zonemanager_fczonemanager


def list_opts():
    return [
        ('FC-ZONE-MANAGER',
            itertools.chain(
                cinder_zonemanager_fczonemanager.zone_manager_opts,
                cinder_zonemanager_drivers_brocade_brcdfczonedriver.brcd_opts,
                cinder_zonemanager_drivers_cisco_ciscofczonedriver.cisco_opts,
            )),
        ('STORAGE_KEYMGR',
            itertools.chain(
                cinder_keymgr_keymgr.encryption_opts,
                jacket.storage.keymgr.keymgr_opts,
                cinder_keymgr_confkeymgr.key_mgr_opts,
            )),
        ('DEFAULT',
            itertools.chain(
                cinder_backup_driver.service_opts,
                cinder_api_common.api_common_opts,
                cinder_backup_drivers_ceph.service_opts,
                cinder_volume_drivers_smbfs.volume_opts,
                cinder_backup_chunkeddriver.chunkedbackup_service_opts,
                cinder_volume_drivers_san_san.san_opts,
                cinder_volume_drivers_hitachi_hnasnfs.NFS_OPTS,
                cinder_wsgi_eventletserver.socket_opts,
                cinder_sshutils.ssh_opts,
                cinder_volume_drivers_netapp_options.netapp_proxy_opts,
                cinder_volume_drivers_netapp_options.netapp_connection_opts,
                cinder_volume_drivers_netapp_options.netapp_transport_opts,
                cinder_volume_drivers_netapp_options.netapp_basicauth_opts,
                cinder_volume_drivers_netapp_options.netapp_cluster_opts,
                cinder_volume_drivers_netapp_options.netapp_7mode_opts,
                cinder_volume_drivers_netapp_options.netapp_provisioning_opts,
                cinder_volume_drivers_netapp_options.netapp_img_cache_opts,
                cinder_volume_drivers_netapp_options.netapp_eseries_opts,
                cinder_volume_drivers_netapp_options.netapp_nfs_extra_opts,
                cinder_volume_drivers_netapp_options.netapp_san_opts,
                cinder_volume_drivers_ibm_storwize_svc_storwizesvciscsi.
                storwize_svc_iscsi_opts,
                cinder_backup_drivers_glusterfs.glusterfsbackup_service_opts,
                cinder_backup_drivers_tsm.tsm_opts,
                cinder_volume_drivers_fujitsu_eternusdxcommon.
                FJ_ETERNUS_DX_OPT_opts,
                cinder_volume_drivers_ibm_gpfs.gpfs_opts,
                cinder_volume_drivers_violin_v7000common.violin_opts,
                cinder_volume_drivers_nexenta_options.NEXENTA_CONNECTION_OPTS,
                cinder_volume_drivers_nexenta_options.NEXENTA_ISCSI_OPTS,
                cinder_volume_drivers_nexenta_options.NEXENTA_DATASET_OPTS,
                cinder_volume_drivers_nexenta_options.NEXENTA_NFS_OPTS,
                cinder_volume_drivers_nexenta_options.NEXENTA_RRMGR_OPTS,
                cinder_volume_drivers_nexenta_options.NEXENTA_EDGE_OPTS,
                cinder_exception.exc_log_opts,
                # cinder_common_config.global_opts,
                cinder_scheduler_weights_capacity.capacity_weight_opts,
                cinder_volume_drivers_sheepdog.sheepdog_opts,
                [cinder_api_middleware_sizelimit.max_request_body_size_opt],
                cinder_volume_drivers_solidfire.sf_opts,
                cinder_backup_drivers_swift.swiftbackup_service_opts,
                cinder_volume_drivers_cloudbyte_options.
                cloudbyte_add_qosgroup_opts,
                cinder_volume_drivers_cloudbyte_options.
                cloudbyte_create_volume_opts,
                cinder_volume_drivers_cloudbyte_options.
                cloudbyte_connection_opts,
                cinder_volume_drivers_cloudbyte_options.
                cloudbyte_update_volume_opts,
                # cinder_service.service_opts,
                jacket.storage.compute.compute_opts,
                cinder_volume_drivers_drbdmanagedrv.drbd_opts,
                cinder_volume_drivers_dothill_dothillcommon.common_opts,
                cinder_volume_drivers_dothill_dothillcommon.iscsi_opts,
                cinder_volume_drivers_glusterfs.volume_opts,
                cinder_volume_drivers_pure.PURE_OPTS,
                cinder_context.context_opts,
                cinder_scheduler_driver.scheduler_driver_opts,
                cinder_volume_drivers_scality.volume_opts,
                cinder_volume_drivers_emc_emcvnxcli.loc_opts,
                cinder_volume_drivers_vmware_vmdk.vmdk_opts,
                cinder_volume_drivers_lenovo_lenovocommon.common_opts,
                cinder_volume_drivers_lenovo_lenovocommon.iscsi_opts,
                cinder_backup_drivers_posix.posixbackup_service_opts,
                cinder_volume_drivers_emc_scaleio.scaleio_opts,
                [cinder_db_base.db_driver_opt],
                cinder_volume_drivers_eqlx.eqlx_opts,
                cinder_transfer_api.volume_transfer_opts,
                cinder_db_api.db_opts,
                cinder_scheduler_weights_volumenumber.
                volume_number_weight_opts,
                cinder_volume_drivers_coho.coho_opts,
                cinder_volume_drivers_xio.XIO_OPTS,
                cinder_volume_drivers_ibm_storwize_svc_storwizesvcfc.
                storwize_svc_fc_opts,
                cinder_volume_drivers_zfssa_zfssaiscsi.ZFSSA_OPTS,
                cinder_volume_driver.volume_opts,
                cinder_volume_driver.iser_opts,
                cinder_api_views_versions.versions_opts,
                cinder_volume_drivers_nimble.nimble_opts,
                cinder_volume_drivers_windows_windows.windows_opts,
                cinder_volume_drivers_san_hp_hpmsacommon.common_opts,
                cinder_volume_drivers_san_hp_hpmsacommon.iscsi_opts,
                cinder_image_glance.glance_opts,
                cinder_image_glance.glance_core_properties_opts,
                cinder_volume_drivers_hpe_hpelefthandiscsi.hpelefthand_opts,
                cinder_volume_drivers_lvm.volume_opts,
                cinder_volume_drivers_emc_emcvmaxcommon.emc_opts,
                cinder_volume_drivers_remotefs.nas_opts,
                cinder_volume_drivers_remotefs.volume_opts,
                cinder_volume_drivers_emc_xtremio.XTREMIO_OPTS,
                cinder_backup_drivers_google.gcsbackup_service_opts,
                # [cinder_api_middleware_auth.use_forwarded_for_opt],
                cinder_volume_drivers_hitachi_hbsdcommon.volume_opts,
                cinder_volume_drivers_infortrend_eonstor_ds_cli_commoncli.
                infortrend_esds_opts,
                cinder_volume_drivers_infortrend_eonstor_ds_cli_commoncli.
                infortrend_esds_extra_opts,
                cinder_volume_drivers_hitachi_hnasiscsi.iSCSI_OPTS,
                cinder_volume_drivers_rbd.rbd_opts,
                cinder_volume_drivers_tintri.tintri_opts,
                cinder_backup_api.backup_api_opts,
                cinder_volume_drivers_hitachi_hbsdhorcm.volume_opts,
                cinder_backup_manager.backup_manager_opts,
                cinder_volume_drivers_ibm_storwize_svc_storwizesvccommon.
                storwize_svc_opts,
                cinder_volume_drivers_hitachi_hbsdfc.volume_opts,
                cinder_quota.quota_opts,
                cinder_volume_drivers_huawei_huaweidriver.huawei_opts,
                cinder_volume_drivers_dell_dellstoragecentercommon.
                common_opts,
                cinder_scheduler_hostmanager.host_manager_opts,
                [cinder_scheduler_manager.scheduler_driver_opt],
                cinder_backup_drivers_nfs.nfsbackup_service_opts,
                cinder_volume_drivers_blockbridge.blockbridge_opts,
                [cinder_scheduler_scheduleroptions.
                    scheduler_json_config_location_opt],
                cinder_volume_drivers_zfssa_zfssanfs.ZFSSA_OPTS,
                cinder_volume_drivers_disco_disco.disco_opts,
                cinder_volume_drivers_hgst.hgst_opts,
                cinder_image_imageutils.image_helper_opts,
                cinder_compute_nova.nova_opts,
                cinder_volume_drivers_ibm_flashsystemfc.flashsystem_fc_opts,
                cinder_volume_drivers_prophetstor_options.DPL_OPTS,
                cinder_volume_drivers_hpe_hpexpopts.FC_VOLUME_OPTS,
                cinder_volume_drivers_hpe_hpexpopts.COMMON_VOLUME_OPTS,
                cinder_volume_drivers_hpe_hpexpopts.HORCM_VOLUME_OPTS,
                cinder_volume_drivers_hitachi_hbsdiscsi.volume_opts,
                cinder_volume_manager.volume_manager_opts,
                cinder_volume_drivers_ibm_flashsystemiscsi.
                flashsystem_iscsi_opts,
                cinder_volume_drivers_tegile.tegile_opts,
                cinder_volume_drivers_ibm_flashsystemcommon.flashsystem_opts,
                [cinder_volume_api.allow_force_upload_opt],
                [cinder_volume_api.volume_host_opt],
                [cinder_volume_api.volume_same_az_opt],
                [cinder_volume_api.az_cache_time_opt],
                cinder_volume_drivers_ibm_xivds8k.xiv_ds8k_opts,
                cinder_volume_drivers_hpe_hpe3parcommon.hpe3par_opts,
                cinder_volume_drivers_datera.d_opts,
                cinder_volume_drivers_blockdevice.volume_opts,
                cinder_volume_drivers_quobyte.volume_opts,
                cinder_volume_drivers_vzstorage.vzstorage_opts,
                cinder_volume_drivers_nfs.nfs_opts,
            )),
        ('CISCO_FABRIC_EXAMPLE',
            itertools.chain(
                cinder_zonemanager_drivers_cisco_ciscofabricopts.
                cisco_zone_opts,
            )),
        ('BRCD_FABRIC_EXAMPLE',
            itertools.chain(
                cinder_zonemanager_drivers_brocade_brcdfabricopts.
                brcd_zone_opts,
            )),
        ('COORDINATION',
            itertools.chain(
                cinder_coordination.coordination_opts,
            )),
        ('BACKEND',
            itertools.chain(
                [cinder_cmd_volume.host_opt],
                [cinder_cmd_all.volume_cmd.host_opt],
            )),
    ]
