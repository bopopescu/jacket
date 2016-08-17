# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
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

"""Defines interface for DB access.

Functions in this module are imported into the cinder.db namespace. Call these
functions from cinder.db namespace, not the cinder.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface. Currently, many of these objects are sqlalchemy objects that
implement a dictionary interface. However, a future goal is to have all of
these objects be simple dictionaries.


**Related Flags**

:connection:  string specifying the sqlalchemy connection to use, like:
              `sqlite:///var/lib/cinder/cinder.sqlite`.

:enable_new_services:  when adding a new service to the database, is it in the
                       pool of available hardware (Default: True)

"""

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import options as db_options

from jacket.common import constants


db_opts = []


CONF = cfg.CONF
CONF.register_opts(db_opts)
db_options.set_defaults(CONF)

_BACKEND_MAPPING = {'sqlalchemy': 'jacket.db.jacket.sqlalchemy.api'}


IMPL = oslo_db_api.DBAPI.from_config(conf=CONF,
                                     backend_mapping=_BACKEND_MAPPING,
                                     lazy=True)

# The maximum value a signed INT type may have
MAX_INT = constants.DB_MAX_INT


def dispose_engine():
    """Force the engine to establish new connections."""

    # FIXME(jdg): When using sqlite if we do the dispose
    # we seem to lose our DB here.  Adding this check
    # means we don't do the dispose, but we keep our sqlite DB
    # This likely isn't the best way to handle this

    if 'sqlite' not in IMPL.get_engine().name:
        return IMPL.dispose_engine()
    else:
        return


def image_mapper_all(context):
    return IMPL.image_mapper_all(context)


def image_mapper_get(context, image_id, project_id):
    return IMPL.image_mapper_get(context, image_id, project_id)


def image_mapper_create(context, image_id, project_id, values):
    return IMPL.image_mapper_create(context, image_id, project_id, values)


def image_mapper_update(context, image_id, project_id, values, delete=True):
    return IMPL.image_mapper_update(context, image_id, project_id, values, delete=delete)


def image_mapper_delete(context, image_id, project_id=None):
    return IMPL.image_mapper_delete(context, image_id, project_id)


def flavor_mapper_all(context):
    return IMPL.flavor_mapper_all(context)


def flavor_mapper_get(context, flavor_id, project_id):
    return IMPL.flavor_mapper_get(context, flavor_id, project_id)


def flavor_mapper_create(context, flavor_id, project_id, values):
    return IMPL.flavor_mapper_create(context, flavor_id, project_id, values)


def flavor_mapper_update(context, flavor_id, project_id, values, delete=True):
    return IMPL.flavor_mapper_update(context, flavor_id, project_id, values, delete=delete)


def flavor_mapper_delete(context, flavor_id, project_id=None):
    return IMPL.flavor_mapper_delete(context, flavor_id, project_id)


def project_mapper_all(context):
    return IMPL.project_mapper_all(context)


def project_mapper_get(context, project_id):
    return IMPL.project_mapper_get(context, project_id)


def project_mapper_create(context, project_id, values):
    return IMPL.project_mapper_create(context, project_id, values)


def project_mapper_update(context, project_id, values, delete=True):
    return IMPL.project_mapper_update(context, project_id, values, delete=delete)


def project_mapper_delete(context, project_id):
    return IMPL.project_mapper_delete(context, project_id)
