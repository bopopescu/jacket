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

from jacket.compute.exception import * # noqu
from jacket.i18n import _
from jacket.exception import JacketException

class MultiInstanceConfusion(JacketException):
    msg_fmt = _("More than one instance are found")


class MultiVolumeConfusion(JacketException):
    msg_fmt = _("More than one volume are found")


class MultiImageConfusion(JacketException):
    msg_fmt = _("More than one Image are found")


class UploadVolumeFailure(JacketException):
    msg_fmt = _("upload volume to provider cloud failure")


class VolumeNotFoundAtProvider(JacketException):
    msg_fmt = _("can not find this volume(%(volume_id)s) at provider cloud")


class VolumeSnapshotNotFoundAtProvider(JacketException):
    msg_fmt = _("can not find this snapshot(%(snapshot_id)s) at provider cloud")


class ProviderRequestTimeOut(JacketException):
    msg_fmt = _("Time out when connect to provider cloud")


class RetryException(JacketException):
    msg_fmt = _('Need to retry, error info: %(error_info)s')


class ServerStatusException(JacketException):
    msg_fmt = _('Server status is error, status: %(status)s')


class ServerStatusTimeoutException(JacketException):
    msg_fmt = _(
        'Server %(server_id)s status is in %(status)s over %(timeout)s seconds')


class ServerNotExistException(JacketException):
    msg_fmt = _('server named  %(server_name)s is not exist')


class ServerDeleteException(JacketException):
    msg_fmt = _('delete server %(server_id)s timeout over %(timeout)s seconds')


class VolumeCreateException(JacketException):
    msg_fmt = _('create volume %(volume_id)s error')


class VolumeStatusTimeoutException(JacketException):
    msg_fmt = _(
        'Volume %(volume_id)s status is in %(status)s over %(timeout)s seconds')


class VolumeDeleteTimeoutException(JacketException):
    msg_fmt = _('delete volume %(volume_id)s timeout')


class VolumeNotExistException(JacketException):
    msg_fmt = _('sub volume of %(volume_id)s is not exist')


class AccountNotConfig(JacketException):
    msg_fmt = _('os account info not config')


class OsCinderVersionNotSupport(JacketException):
    msg_fmt = _("os cinder version%(version)s not support.")


class OsCinderConnectFailed(JacketException):
    msg_fmt = _("connect os cinder failed!")


class OsVolumeNotFound(NotFound):
    msg_fmt = _("Os Volume %(volume_id)s could not be found.")


class OsSnapshotNotFound(NotFound):
    msg_fmt = _("Os Snapshot %(snapshot_id)s could not be found.")


class OsInvalidVolume(Invalid):
    msg_fmt = _("Invalid volume: %(reason)s")


class OsVolumeUnattached(Invalid):
    msg_fmt = _("Volume %(volume_id)s is not attached to anything")


class OsOverQuota(JacketException):
    msg_fmt = _("Quota exceeded for resources: %(overs)s")


class OsNovaVersionNotSupport(JacketException):
    msg_fmt = _("os nova version%(version)s not support.")


class OsNovaNotUserOrPass(JacketException):
    msg_fmt = _("os nova username or password is illegal.")


class OsNovaConnectFailed(JacketException):
    msg_fmt = _("connect os nova failed!")


class OsInvalidServiceVersion(JacketException):
    msg_fmt = _("Invalid service %(service)s version %(version)s")