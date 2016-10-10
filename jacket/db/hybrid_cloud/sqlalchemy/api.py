# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2014 IBM Corp.
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

"""Implementation of SQLAlchemy backend."""


import collections
import datetime as dt
import functools
import itertools
import re
import sys
import threading
import time
import uuid

from oslo_config import cfg
from oslo_db import api as oslo_db_api
from oslo_db import exception as db_exc
from oslo_db import options
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging
from oslo_utils import importutils
osprofiler_sqlalchemy = importutils.try_import('osprofiler.sqlalchemy')
import sqlalchemy
from sqlalchemy import or_, and_, case
from sqlalchemy.sql import null
from oslo_db.sqlalchemy import utils as sqlalchemyutils

import jacket.context
from jacket.db.hybrid_cloud.sqlalchemy import models
from jacket import exception
from jacket.i18n import _, _LW, _LE, _LI


CONF = cfg.CONF
LOG = logging.getLogger(__name__)

options.set_defaults(CONF, connection='sqlite:///$state_path/jacket.sqlite')

_LOCK = threading.Lock()
_FACADE = None


def _create_facade_lazily():
    global _LOCK
    with _LOCK:
        global _FACADE
        if _FACADE is None:
            _FACADE = db_session.EngineFacade(
                CONF.database.connection,
                **dict(CONF.database)
            )

            # NOTE(geguileo): To avoid a cyclical dependency we import the
            # group here.  Dependency cycle is objects.base requires db.api,
            # which requires db.sqlalchemy.api, which requires service which
            # requires objects.base
            CONF.import_group("profiler", "jacket.service")
            if CONF.profiler.enabled:
                if CONF.profiler.trace_sqlalchemy:
                    osprofiler_sqlalchemy.add_tracing(sqlalchemy,
                                                      _FACADE.get_engine(),
                                                      "db")

        return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def dispose_engine():
    get_engine().dispose()

_DEFAULT_QUOTA_NAME = 'default'


def get_backend():
    """The backend is this module itself."""

    return sys.modules[__name__]


def _retry_on_deadlock(f):
    """Decorator to retry a DB API call if Deadlock was received."""
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        while True:
            try:
                return f(*args, **kwargs)
            except db_exc.DBDeadlock:
                LOG.warning(_LW("Deadlock detected when running "
                                "'%(func_name)s': Retrying..."),
                            dict(func_name=f.__name__))
                # Retry!
                time.sleep(0.5)
                continue
    functools.update_wrapper(wrapped, f)
    return wrapped


def handle_db_data_error(f):
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except db_exc.DBDataError:
            msg = _('Error writing field to database')
            LOG.exception(msg)
            raise exception.Invalid(msg)

    return wrapper


def require_context(f):
    """Decorator to require *any* user or admin context.

    This does no authorization for user or project access matching, see
    :py:func:`nova.context.authorize_project_context` and
    :py:func:`nova.context.authorize_user_context`.

    The first argument to the wrapped function must be the context.

    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        jacket.context.require_context(args[0])
        return f(*args, **kwargs)
    return wrapper


def model_query(context, model,
                args=None,
                read_deleted=None,
                project_only=False,
                session=None):
    """Query helper that accounts for context's `read_deleted` field.

    :param context:     NovaContext of the query.
    :param model:       Model to query. Must be a subclass of ModelBase.
    :param args:        Arguments to query. If None - model is used.
    :param read_deleted: If not None, overrides context's read_deleted field.
                        Permitted values are 'no', which does not return
                        deleted values; 'only', which only returns deleted
                        values; and 'yes', which does not filter deleted
                        values.
    :param project_only: If set and context is user-type, then restrict
                        query to match the context's project_id. If set to
                        'allow_none', restriction includes project_id = None.
    """

    if read_deleted is None:
        read_deleted = context.read_deleted

    query_kwargs = {}
    if 'no' == read_deleted:
        query_kwargs['deleted'] = False
    elif 'only' == read_deleted:
        query_kwargs['deleted'] = True
    elif 'yes' == read_deleted:
        pass
    else:
        raise ValueError(_("Unrecognized read_deleted value '%s'")
                           % read_deleted)

    query = sqlalchemyutils.model_query(
        model, session or get_session(), args, **query_kwargs)

    # We can't use oslo.db model_query's project_id here, as it doesn't allow
    # us to return both our projects and unowned projects.
    if jacket.context.is_user_context(context) and project_only:
        if project_only == 'allow_none':
            query = query.\
                filter(or_(model.project_id == context.project_id,
                           model.project_id == null()))
        else:
            query = query.filter_by(project_id=context.project_id)

    return query


###################


def _mapper_convert_dict(key_values):
    keys = ['image_id', 'flavor_id',
            'project_id', 'instance_id', 'volume_id', 'snapshot_id']
    ret = {}
    for key_value in key_values:
        temp_key = None
        temp_value = None
        for key, value in key_value.iteritems():
            if key in keys:
                ret[key] = value
            if key == 'key':
                temp_key = value
            if key == 'value':
                temp_value = value

        if temp_key:
            ret[temp_key] = temp_value

    return ret


def image_mapper_all(context):
    query = model_query(context, models.ImagesMapper, read_deleted="no")
    images_mapper = query.all()
    image_ids = set([image_mapper['image_id'] for image_mapper in images_mapper])
    ret = []
    for image_id in image_ids:
        key_values = query.filter_by(image_id=image_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def image_mapper_get(context, image_id, project_id=None):
    query = model_query(context, models.ImagesMapper, read_deleted="no")
    key_values = query.filter_by(image_id=image_id).all()
    return _mapper_convert_dict(key_values)


def _image_mapper_convert_objs(image_id, project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.ImagesMapper()
            value_ref.image_id = image_id
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.ImagesMapper()
        value_ref.image_id = image_id
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def image_mapper_create(context, image_id, project_id, values):
    value_refs = _image_mapper_convert_objs(image_id, project_id, values)
    for value in value_refs:
        value.save(get_session())

    return image_mapper_get(context, image_id, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def image_mapper_update(context, image_id, project_id, values, delete=False):
    session = get_session()
    query = model_query(context, models.ImagesMapper, read_deleted="no",
                        session=session).\
        filter_by(image_id=image_id)
    all_keys = values.keys()

    cur_project_id = project_id

    if 'project_id' in all_keys:
        all_keys.remove('project_id')
        cur_project_id = values.pop('project_id')
        query.update({'project_id': cur_project_id})

    if delete:
        query.filter(~models.ImagesMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.ImagesMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.ImagesMapper()
        update_ref.update({"image_id": image_id,
                           "project_id": cur_project_id,
                           "key": key,
                           "value": values[key]})
        update_ref.save(session)

    return image_mapper_get(context, image_id, project_id)


def image_mapper_delete(context, image_id, project_id=None):
    query = model_query(context, models.ImagesMapper, read_deleted="no")
    query.filter_by(image_id=image_id).soft_delete()


def flavor_mapper_all(context):
    query = model_query(context, models.FlavorsMapper, read_deleted="no")
    flavors_mapper = query.all()
    flavor_ids = set([flavor_mapper['flavor_id'] for flavor_mapper in flavors_mapper])
    ret = []
    for flavor_id in flavor_ids:
        key_values = query.filter_by(flavor_id=flavor_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def flavor_mapper_get(context, flavor_id, project_id=None):
    query = model_query(context, models.FlavorsMapper, read_deleted="no")
    key_values = query.filter_by(flavor_id=flavor_id).all()
    return _mapper_convert_dict(key_values)


def _flavor_mapper_convert_objs(flavor_id, project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.FlavorsMapper()
            value_ref.flavor_id = flavor_id
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.FlavorsMapper()
        value_ref.flavor_id = flavor_id
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def flavor_mapper_create(context, flavor_id, project_id, values):
    value_refs = _flavor_mapper_convert_objs(flavor_id, project_id, values)
    for value in value_refs:
        value.save(get_session())

    return flavor_mapper_get(context, flavor_id, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def flavor_mapper_update(context, flavor_id, project_id, values, delete=False):
    session = get_session()
    query = model_query(context, models.FlavorsMapper, read_deleted="no",
                        session=session).\
        filter_by(flavor_id=flavor_id)
    all_keys = values.keys()

    cur_project_id = project_id

    if 'project_id' in all_keys:
        all_keys.remove('project_id')
        cur_project_id = values.pop('project_id')
        query.update({'project_id': cur_project_id})

    if delete:
        query.filter(~models.FlavorsMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.FlavorsMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.FlavorsMapper()
        update_ref.flavor_id = flavor_id
        update_ref.project_id = cur_project_id
        update_ref['key'] = key
        update_ref['value'] = values[key]
        update_ref.save(session)

    return flavor_mapper_get(context, flavor_id, project_id)


def flavor_mapper_delete(context, flavor_id, project_id):
    query = model_query(context, models.FlavorsMapper, read_deleted="no")
    query.filter_by(flavor_id=flavor_id, project_id=project_id).soft_delete()


def project_mapper_all(context):
    query = model_query(context, models.ProjectsMapper, read_deleted="no")
    projects_mapper = query.all()
    project_ids = set([project_mapper['project_id'] for project_mapper in projects_mapper])
    ret = []
    for project_id in project_ids:
        key_values = query.filter_by(project_id=project_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def project_mapper_get(context, project_id):
    query = model_query(context, models.ProjectsMapper, read_deleted="no")
    key_values = query.filter_by(project_id=project_id).all()
    return _mapper_convert_dict(key_values)


def _project_mapper_convert_objs(project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.ProjectsMapper()
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.ProjectsMapper()
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def project_mapper_create(context, project_id, values):
    value_refs = _project_mapper_convert_objs(project_id, values)
    for value in value_refs:
        value.save(get_session())

    return project_mapper_get(context, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def project_mapper_update(context, project_id, values, delete=False):
    session = get_session()
    query = model_query(context, models.ProjectsMapper, read_deleted="no",
                        session=session).\
        filter_by(project_id=project_id)
    all_keys = values.keys()
    if delete:
        query.filter(~models.ProjectsMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.ProjectsMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.ProjectsMapper()
        update_ref.update({"project_id": project_id,
                           "key": key,
                           "value": values[key]})
        update_ref.save(session)

    return project_mapper_get(context, project_id)


def project_mapper_delete(context, project_id):
    query = model_query(context, models.ProjectsMapper, read_deleted="no")
    query.filter_by(project_id=project_id).soft_delete()


def instance_mapper_all(context):
    query = model_query(context, models.InstancesMapper, read_deleted="no")
    instances_mapper = query.all()
    instance_ids = set([instance_mapper['instance_id'] for instance_mapper in
                     instances_mapper])
    ret = []
    for instance_id in instance_ids:
        key_values = query.filter_by(instance_id=instance_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def instance_mapper_get(context, instance_id, project_id=None):
    query = model_query(context, models.InstancesMapper, read_deleted="no")
    key_values = query.filter_by(instance_id=instance_id).all()
    return _mapper_convert_dict(key_values)


def _instance_mapper_convert_objs(instance_id, project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.InstancesMapper()
            value_ref.instance_id = instance_id
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.InstancesMapper()
        value_ref.instance_id = instance_id
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def instance_mapper_create(context, instance_id, project_id, values):
    value_refs = _instance_mapper_convert_objs(instance_id, project_id, values)
    for value in value_refs:
        value.save(get_session())

    return instance_mapper_get(context, instance_id, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def instance_mapper_update(context, instance_id, project_id, values, delete=False):
    session = get_session()
    query = model_query(context, models.InstancesMapper, read_deleted="no",
                        session=session).\
        filter_by(instance_id=instance_id)
    all_keys = values.keys()

    cur_project_id = project_id

    if 'project_id' in all_keys:
        all_keys.remove('project_id')
        cur_project_id = values.pop('project_id')
        query.update({'project_id': cur_project_id})

    if delete:
        query.filter(~models.InstancesMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.InstancesMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.InstancesMapper()
        update_ref.update({"instance_id": instance_id,
                           "project_id": cur_project_id,
                           "key": key,
                           "value": values[key]})
        update_ref.save(session)

    return instance_mapper_get(context, instance_id, project_id)


def instance_mapper_delete(context, instance_id, project_id=None):
    query = model_query(context, models.InstancesMapper, read_deleted="no")
    query.filter_by(instance_id=instance_id).soft_delete()


def volume_mapper_all(context):
    query = model_query(context, models.VolumesMapper, read_deleted="no")
    volumes_mapper = query.all()
    volume_ids = set([volume_mapper['volume_id'] for volume_mapper in
                     volumes_mapper])
    ret = []
    for volume_id in volume_ids:
        key_values = query.filter_by(volume_id=volume_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def volume_mapper_get(context, volume_id, project_id=None):
    query = model_query(context, models.VolumesMapper, read_deleted="no")
    key_values = query.filter_by(volume_id=volume_id).all()
    return _mapper_convert_dict(key_values)


def _volume_mapper_convert_objs(volume_id, project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.VolumesMapper()
            value_ref.volume_id = volume_id
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.VolumesMapper()
        value_ref.volume_id = volume_id
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def volume_mapper_create(context, volume_id, project_id, values):
    value_refs = _volume_mapper_convert_objs(volume_id, project_id, values)
    for value in value_refs:
        value.save(get_session())

    return volume_mapper_get(context, volume_id, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def volume_mapper_update(context, volume_id, project_id, values, delete=False):
    session = get_session()
    query = model_query(context, models.VolumesMapper, read_deleted="no",
                        session=session).\
        filter_by(volume_id=volume_id)
    all_keys = values.keys()

    cur_project_id = project_id

    if 'project_id' in all_keys:
        all_keys.remove('project_id')
        cur_project_id = values.pop('project_id')
        query.update({'project_id': cur_project_id})

    if delete:
        query.filter(~models.VolumesMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.VolumesMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.VolumesMapper()
        update_ref.update({"volume_id": volume_id,
                           "project_id": cur_project_id,
                           "key": key,
                           "value": values[key]})
        update_ref.save(session)

    return volume_mapper_get(context, volume_id, project_id)


def volume_mapper_delete(context, volume_id, project_id=None):
    query = model_query(context, models.VolumesMapper, read_deleted="no")
    query.filter_by(volume_id=volume_id).soft_delete()


def volume_snapshot_mapper_all(context):
    query = model_query(context, models.VolumeSnapshotsMapper, read_deleted="no")
    volume_snapshots_mapper = query.all()
    volume_snapshot_ids = set([volume_snapshot_mapper['volume_snapshot_id']
                               for volume_snapshot_mapper in
                               volume_snapshots_mapper])
    ret = []
    for volume_snapshot_id in volume_snapshot_ids:
        key_values = query.filter_by(snapshot_id=volume_snapshot_id).all()
        ret.append(_mapper_convert_dict(key_values))
    return ret


def volume_snapshot_mapper_get(context, snapshot_id, project_id=None):
    query = model_query(context, models.VolumeSnapshotsMapper, read_deleted="no")
    key_values = query.filter_by(snapshot_id=snapshot_id).all()
    return _mapper_convert_dict(key_values)


def _volume_snapshot_mapper_convert_objs(snapshot_id, project_id, values_dict):
    value_refs = []
    if values_dict:
        for k, v in values_dict.items():
            value_ref = models.VolumeSnapshotsMapper()
            value_ref.snapshot_id = snapshot_id
            value_ref.project_id = project_id
            value_ref['key'] = k
            value_ref['value'] = v
            value_refs.append(value_ref)
    else:
        value_ref = models.VolumeSnapshotsMapper()
        value_ref.snapshot_id = snapshot_id
        value_ref.project_id = project_id
        value_refs.append(value_ref)
    return value_refs


def volume_snapshot_mapper_create(context, snapshot_id, project_id, values):
    value_refs = _volume_snapshot_mapper_convert_objs(snapshot_id, project_id,
                                                      values)
    for value in value_refs:
        value.save(get_session())

    return volume_snapshot_mapper_get(context, snapshot_id, project_id)


@require_context
@oslo_db_api.wrap_db_retry(max_retries=5, retry_on_deadlock=True)
def volume_snapshot_mapper_update(context, snapshot_id, project_id, values,
                                  delete=False):
    session = get_session()
    query = model_query(context, models.VolumeSnapshotsMapper, read_deleted="no",
                        session=session).\
        filter_by(snapshot_id=snapshot_id)
    all_keys = values.keys()

    cur_project_id = project_id

    if 'project_id' in all_keys:
        all_keys.remove('project_id')
        cur_project_id = values.pop('project_id')
        query.update({'project_id': cur_project_id})

    if delete:
        query.filter(~models.VolumeSnapshotsMapper.key.in_(all_keys)).\
            soft_delete(synchronize_session=False)

    already_existing_keys = []
    mod_refs = query.filter(models.VolumeSnapshotsMapper.key.in_(all_keys)).all()
    for one in mod_refs:
        already_existing_keys.append(one.key)
        one.update({"value": values[one.key]})
        one.save(session)

    new_keys = set(all_keys) - set(already_existing_keys)
    for key in new_keys:
        update_ref = models.VolumeSnapshotsMapper()
        update_ref.update({"snapshot_id": snapshot_id,
                           "project_id": cur_project_id,
                           "key": key,
                           "value": values[key]})
        update_ref.save(session)

    return volume_snapshot_mapper_get(context, snapshot_id, project_id)


def volume_snapshot_mapper_delete(context, snapshot_id, project_id=None):
    query = model_query(context, models.VolumeSnapshotsMapper, read_deleted="no")
    query.filter_by(snapshot_id=snapshot_id).soft_delete()