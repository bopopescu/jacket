
import copy

from oslo_log import log as logging

from jacket import exception
from jacket.db.hybrid_cloud import api as db_api
from jacket.i18n import _LE


LOG = logging.getLogger(__name__)


class FsClientContext(object):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """

    def __init__(self, context, version=None, username=None, password=None,
                 project_id=None, auth_url='', service_type=None,
                 service_name=None, interface=None,
                 region_name=None, **kwargs):

        try:
            self.init_fs_context(context)
        except Exception:
            self.context = context
            self.version = version
            self.username = username
            self.password = password
            self.project_id = project_id
            self.auth_url = auth_url
            self.service_type = service_type
            self.service_name = service_name
            self.interface = interface
            self.region_name = region_name
            self.insecure = kwargs.pop('insecure', None)
            self.cacert = kwargs.pop('cacert', None)
            self.timeout = kwargs.pop('timeout', None)
            self.kwargs = kwargs

    def to_dict(self):
        values = {}
        values.update({
            'version': getattr(self, 'version', None),
            'username': getattr(self, 'username', None),
            'password': getattr(self, 'password', None),
            'project_id': getattr(self, 'project_id', None),
            'auth_url': getattr(self, 'auth_url', None),
            'service_type': getattr(self, 'service_type', None),
            'interface': getattr(self, 'interface', None),
            'region_name': getattr(self, 'region_name', None),
            'insecure': getattr(self, 'insecure', None),
            'cacert': getattr(self, 'cacert', None),
            'timeout': getattr(self, 'timeout', None),
        })

        if self.kwargs:
            for k, v in self.kwargs.iteritems():
                values.update({k: v})
        return values

    def elevated(self, read_deleted=None):
        """Return a version of this context with admin flag set."""
        context = copy.copy(self)

        return context

    def __str__(self):
        return "<FsContext %s>" % self.to_dict()

    def init_fs_context(self, context):
        try:
            project_info = db_api.project_mapper_get(context, context.project_id)
        except Exception as ex:
            LOG.exception(_LE("get project info failed, ex = %s"), ex)
            project_info = db_api.project_mapper_get(context,
                                                     "default")

        LOG.debug("+++hw, project_info = %s", project_info)

        if project_info == None:
            raise exception.FsProjectNotConf()

        self.version = project_info.pop('version', None)
        self.username = project_info.pop('username', None)
        self.password = project_info.pop("password", None)
        self.project_id = project_info.pop("project_id", None)
        self.auth_url = project_info.pop("auth_url", None)
        self.region_name = project_info.pop("region_name", None)

        if not self.username or not self.password or not self.project_id or \
            not self.auth_url:
            raise exception.FsProjectNotConf()

        self.service_type = project_info.pop("service_type", None)
        self.service_name = project_info.pop("service_name", None)
        self.interface = project_info.pop("interface", None)

        self.kwargs = project_info

    def auth_needs_refresh(self):
        return False
