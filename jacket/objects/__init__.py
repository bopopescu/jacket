# NOTE(nkapotoxin): All jacket objects are registered, an attribute is set
# on this module automatically, pointing to the newest/latest version of
# the object.

from jacket.objects import compute
from jacket.objects import storage


def register_all():
    compute.register_all()
    storage.register_all()
