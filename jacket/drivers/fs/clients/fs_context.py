
import copy


class FsClientContext(object):
    """Security context and request information.

    Represents the user taking a given action within the system.

    """

    def __init__(self, context, version=None, username=None, password=None, project_id=None,
                 auth_url='', service_type=None, service_name=None, interface=None,
                 region_name=None, **kwargs):

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
        return "<Context %s>" % self.to_dict()