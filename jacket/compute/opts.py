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

import jacket.compute.baserpc
import jacket.compute.cloudpipe.pipelib
import jacket.cmd.compute.novnc
import jacket.cmd.compute.serialproxy
import jacket.cmd.compute.spicehtml5proxy
import jacket.compute.conductor.rpcapi
import jacket.compute.conductor.tasks.live_migrate
import jacket.compute.conf
import jacket.compute.console.manager
import jacket.compute.console.rpcapi
import jacket.compute.console.serial
import jacket.compute.console.xvp
import jacket.compute.consoleauth
import jacket.compute.consoleauth.manager
import jacket.compute.consoleauth.rpcapi
import jacket.compute.crypto
import jacket.db.compute.api
import jacket.db.compute.base
import jacket.db.compute.sqlalchemy.api
import jacket.compute.exception
import jacket.compute.image.download.file
import jacket.compute.image.glance
import jacket.compute.ipv6.api
import jacket.compute.keymgr
import jacket.compute.keymgr.barbican
import jacket.compute.keymgr.conf_key_mgr
import jacket.compute.netconf
import jacket.compute.notifications
import jacket.objects.compute.network
import jacket.compute.paths
import jacket.compute.quota
import jacket.compute.rdp
import jacket.compute.service
import jacket.compute.servicegroup.api
import jacket.compute.spice
import jacket.compute.utils
import jacket.compute.volume
import jacket.compute.volume.cinder


def list_opts():
    return [
        ('DEFAULT',
         itertools.chain(
             [jacket.compute.conductor.tasks.live_migrate.migrate_opt],
             [jacket.compute.consoleauth.consoleauth_topic_opt],
             [jacket.db.compute.base.db_driver_opt],
             [jacket.compute.ipv6.api.ipv6_backend_opt],
             [jacket.compute.servicegroup.api.servicegroup_driver_opt],
             jacket.compute.cloudpipe.pipelib.cloudpipe_opts,
             jacket.cmd.compute.novnc.opts,
             jacket.compute.console.manager.console_manager_opts,
             jacket.compute.console.rpcapi.rpcapi_opts,
             jacket.compute.console.xvp.xvp_opts,
             jacket.compute.consoleauth.manager.consoleauth_opts,
             jacket.compute.crypto.crypto_opts,
             jacket.db.compute.api.db_opts,
             jacket.db.compute.sqlalchemy.api.db_opts,
             jacket.compute.exception.exc_log_opts,
             jacket.compute.netconf.netconf_opts,
             jacket.compute.notifications.notify_opts,
             jacket.objects.compute.network.network_opts,
             jacket.compute.paths.path_opts,
             jacket.compute.quota.quota_opts,
             jacket.compute.service.service_opts,
             jacket.compute.utils.monkey_patch_opts,
             jacket.compute.utils.utils_opts,
             jacket.compute.volume._volume_opts,
         )),
        ('barbican', jacket.compute.keymgr.barbican.barbican_opts),
        ('cinder', jacket.compute.volume.cinder.cinder_opts),
        ('api_database', jacket.db.compute.sqlalchemy.api.api_db_opts),
        ('database', jacket.db.compute.sqlalchemy.api.oslo_db_options.database_opts),
        ('glance', jacket.compute.image.glance.glance_opts),
        ('image_file_url', [jacket.compute.image.download.file.opt_group]),
        ('keymgr',
         itertools.chain(
             jacket.compute.keymgr.conf_key_mgr.key_mgr_opts,
             jacket.compute.keymgr.keymgr_opts,
         )),
        ('rdp', jacket.compute.rdp.rdp_opts),
        ('spice',
         itertools.chain(
             jacket.cmd.compute.spicehtml5proxy.opts,
             jacket.compute.spice.spice_opts,
         )),
        ('upgrade_levels',
         itertools.chain(
             [jacket.compute.baserpc.rpcapi_cap_opt],
             [jacket.compute.conductor.rpcapi.rpcapi_cap_opt],
             [jacket.compute.console.rpcapi.rpcapi_cap_opt],
             [jacket.compute.consoleauth.rpcapi.rpcapi_cap_opt],
         )),
        ('workarounds', jacket.compute.utils.workarounds_opts),
    ]
