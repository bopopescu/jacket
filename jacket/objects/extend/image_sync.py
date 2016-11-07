#    Copyright 2013 IBM Corp.
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

from oslo_log import log as logging

from jacket.db import extend as db
from jacket import exception
from jacket.objects import base
from jacket.objects import extend as objects
from jacket.objects import fields

LOG = logging.getLogger(__name__)


@base.JacketObjectRegistry.register
class ImageSync(base.JacketPersistentObject, base.JacketObject,
                base.JacketObjectDictCompat):
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(),
        'image_id': fields.StringField(nullable=True),
        'project_id': fields.StringField(nullable=True),
        'volume_id': fields.StringField(nullable=True),
        'status': fields.StringField(nullable=True),
    }

    @staticmethod
    def _from_db_object(context, image_sync, db_image_sync):
        for key in image_sync.fields:
            value = db_image_sync[key]
            image_sync[key] = value

        image_sync._context = context
        image_sync.obj_reset_changes()
        return image_sync

    @classmethod
    def get_by_image_id(cls, context, image_id):
        db_image_sync = db.image_sync_get(context, image_id)
        return cls._from_db_object(context, cls(), db_image_sync)

    @base.remotable
    def create(self):
        if self.obj_attr_is_set('id'):
            raise exception.ObjectActionError(action='create',
                                              reason='already created')
        updates = self.obj_get_changes()
        db_image_sync = db.image_sync_create(self._context, updates)
        self._from_db_object(self._context, self, db_image_sync)

    def save(self):
        updates = self.obj_get_changes()
        updates.pop('id', None)
        LOG.debug("updates = %s", updates)
        db_image_sync = db.image_sync_update(self._context, self.image_id,
                                             updates)
        self._from_db_object(self._context, self, db_image_sync)
        self.obj_reset_changes()

    def destroy(self):
        db.image_sync_delete(self._context, self.image_id)

@base.JacketObjectRegistry.register
class ImageSyncList(base.ObjectListBase, base.JacketObject):
    # Version 1.0: Initial version

    VERSION = '1.0'

    fields = {
        'objects': fields.ListOfObjectsField('ImageSync'),
    }

    @base.remotable_classmethod
    def get_by_filters(cls, context, filters):
        db_image_syncs = db.image_sync_get_all_by_filters(context, filters)
        return base.obj_make_list(context, cls(context), objects.ImageSync,
                                  db_image_syncs)
