__author__ = 'wangfeng'

from jacket.compute.exception import *
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
    msg_fmt = _("can not find this volume at provider cloud")


class ProviderRequestTimeOut(JacketException):
    msg_fmt = _("Time out when connect to provider cloud")


class RetryException(JacketException):
    msg_fmt = _('Need to retry, error info: %(error_info)s')


class ServerStatusException(JacketException):
    msg_fmt = _('Server status is error, status: %(status)s')


class ServerStatusTimeoutException(JacketException):
    msg_fmt = _('Server %(server_id)s status is in %(status)s'
                'over %(timeout)s seconds')


class ServerNotExistException(JacketException):
    msg_fmt = _('server named  %(server_name)s is not exist')


class ServerDeleteException(JacketException):
    msg_fmt = _('delete server %(server_id)s timeout over %(timeout)s seconds')


class VolumeCreateException(JacketException):
    msg_fmt = _('create volume %(volume_id)s error')


class VolumeStatusTimeoutException(JacketException):
    msg_fmt = _('Volume %(volume_id)s status is in %(status)s'
                'over %(timeout)s seconds')


class VolumeDeleteTimeoutException(JacketException):
    msg_fmt = _('delete volume %(volume_id)s timeout')
