# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
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

"""jacket base exception handling.

Includes decorator for re-raising jacket-type exceptions.

SHOULD include dedicated exception logging.

"""

import sys

from oslo_config import cfg
from oslo_log import log as logging
import six
import webob.exc
from webob import util as woutil

from jacket.i18n import _, _LE

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class ConvertedException(webob.exc.WSGIHTTPException):
    def __init__(self, code, title="", explanation=""):
        self.code = code
        # There is a strict rule about constructing status line for HTTP:
        # '...Status-Line, consisting of the protocol version followed by a
        # numeric status code and its associated textual phrase, with each
        # element separated by SP characters'
        # (http://www.faqs.org/rfcs/rfc2616.html)
        # 'code' and 'title' can not be empty because they correspond
        # to numeric status code and its associated text
        if title:
            self.title = title
        else:
            try:
                self.title = woutil.status_reasons[self.code]
            except KeyError:
                msg = _LE("Improper or unknown HTTP status code used: %d")
                LOG.error(msg, code)
                self.title = woutil.status_generic_reasons[self.code // 100]
        self.explanation = explanation
        super(ConvertedException, self).__init__()


class JacketException(Exception):
    """Base jacket Exception

    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.

    """
    msg_fmt = _("An unknown exception occurred.")
    code = 500
    headers = {}
    safe = False

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                exc_info = sys.exc_info()
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception(_LE('Exception in string format operation'))
                for name, value in six.iteritems(kwargs):
                    LOG.error("%s: %s" % (name, value))  # noqa

                if CONF.fatal_exception_format_errors:
                    six.reraise(*exc_info)
                else:
                    # at least get the core message out if something happened
                    message = self.msg_fmt

        self.message = message
        super(JacketException, self).__init__(message)

    def format_message(self):
        # NOTE(mrodden): use the first argument to the python Exception object
        # which should be our full JacketException message, (see __init__)
        return self.args[0]


class Forbidden(JacketException):
    msg_fmt = _("Forbidden")
    code = 403


class AdminRequired(Forbidden):
    msg_fmt = _("User does not have admin privileges")


class PolicyNotAuthorized(Forbidden):
    msg_fmt = _("Policy doesn't allow %(action)s to be performed.")


class Invalid(JacketException):
    msg_fmt = _("Bad Request - Invalid Parameters")
    code = 400


class InvalidAttribute(Invalid):
    msg_fmt = _("Attribute not supported: %(attr)s")


class ValidationError(Invalid):
    msg_fmt = "%(detail)s"


class InvalidRequest(Invalid):
    msg_fmt = _("The request is invalid.")


class InvalidInput(Invalid):
    msg_fmt = _("Invalid input received: %(reason)s")


class InvalidIpProtocol(Invalid):
    msg_fmt = _("Invalid IP protocol %(protocol)s.")


class InvalidContentType(Invalid):
    msg_fmt = _("Invalid content type %(content_type)s.")


class InvalidAPIVersionString(Invalid):
    msg_fmt = _("API Version String %(version)s is of invalid format. Must "
                "be of format MajorNum.MinorNum.")


class VersionNotFoundForAPIMethod(Invalid):
    msg_fmt = _("API version %(version)s is not supported on this method.")


class InvalidGlobalAPIVersion(Invalid):
    msg_fmt = _("Version %(req_ver)s is not supported by the API. Minimum "
                "is %(min_ver)s and maximum is %(max_ver)s.")


class ApiVersionsIntersect(Invalid):
    msg_fmt = _("Version of %(name)s %(min_ver)s %(max_ver)s intersects "
                "with another versions.")


# Cannot be templated as the error syntax varies.
# msg needs to be constructed when raised.
class InvalidParameterValue(Invalid):
    msg_fmt = _("%(err)s")


class InvalidStrTime(Invalid):
    msg_fmt = _("Invalid datetime string: %(reason)s")


class InvalidName(Invalid):
    msg_fmt = _("An invalid 'name' value was provided. "
                "The name must be: %(reason)s")


class OrphanedObjectError(JacketException):
    msg_fmt = _('Cannot call %(method)s on orphaned %(objtype)s object')


class ConfigNotFound(JacketException):
    msg_fmt = _("Could not find config at %(path)s")


class PasteAppNotFound(JacketException):
    msg_fmt = _("Could not load paste app '%(name)s' from %(path)s")


class ServiceNotFound(JacketException):
    msg_fmt = _("Service %(service_id)s could not be found.")


class ServiceBinaryExists(JacketException):
    msg_fmt = _("Service with host %(host)s binary %(binary)s exists.")


class ServiceTopicExists(JacketException):
    msg_fmt = _("Service with host %(host)s topic %(topic)s exists.")


class QuotaError(JacketException):
    ec2_code = 'ResourceLimitExceeded'
    msg_fmt = _("Quota exceeded: code=%(code)s")
    # NOTE(cyeoh): 413 should only be used for the ec2 API
    # The error status code for out of quota for the compute api should be
    # 403 Forbidden.
    code = 413
    safe = True


class MalformedRequestBody(JacketException):
    msg_fmt = _("Malformed message body: %(reason)s")


class NotFound(JacketException):
    msg_fmt = _("Resource could not be found.")
    code = 404


class NoUniqueMatch(JacketException):
    """Multiple entities found instead of one."""
    pass


class NotAuthorized(JacketException):
    msg_fmt = _("Not authorized.")
    code = 403


class DriverNotSupported(JacketException):
    msg_fmt = _("driver is not supported.")


class EntityNotFound(JacketException):
    msg_fmt = _("The %(entity)s (%(name)s) could not be found.")

    def __init__(self, entity=None, name=None, **kwargs):
        self.entity = entity
        self.name = name
        super(EntityNotFound, self).__init__(entity=entity, name=name,
                                             **kwargs)


class ResourceInError(JacketException):
    msg_fmt = _('Went to status %(resource_status)s '
                'due to "%(status_reason)s"')

    def __init__(self, status_reason=_('Unknown'), **kwargs):
        super(ResourceInError, self).__init__(status_reason=status_reason,
                                              **kwargs)


class ResourceUnknownStatus(JacketException):
    msg_fmt = _('%(result)s - Unknown status %(resource_status)s due to '
                '"%(status_reason)s"')

    def __init__(self, result=_('Resource failed'),
                 status_reason=_('Unknown'), **kwargs):
        super(ResourceUnknownStatus, self).__init__(
            result=result, status_reason=status_reason, **kwargs)


class Error(JacketException):
    msg_fmt = _("%(message)s")

    def __init__(self, msg):
        super(Error, self).__init__(message=msg)


class ImageSyncNotFound(JacketException):
    msg_fmt = _("image(%(image_id)s sync not found.")