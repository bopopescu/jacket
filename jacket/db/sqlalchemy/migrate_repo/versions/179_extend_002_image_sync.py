# Copyright 2012 OpenStack Foundation
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

from migrate.changeset import UniqueConstraint
from oslo_config import cfg
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index
from sqlalchemy import Integer, MetaData, String, Table, Text

# Get default values via config.  The defaults will either
# come from the default values set in the quota option
# configuration or via cinder.conf if the user has configured
# default values for quotas there.
CONF = cfg.CONF


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    image_sync = Table(
        'imge_sync', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('image_id', String(36), nullable=False),
        Column('project_id', String(255)),
        Column('volume_id', String(36)),
        Column('status', String(36)),
        Index('image_id_deleted_idx', 'image_id', 'deleted'),
        Index('image_id_az_deleted_idx', 'image_id', 'project_id',
              'deleted'),
        UniqueConstraint('image_id', 'project_id', 'deleted'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    image_sync.create()


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine
    image_sync = Table('imge_sync', meta, autoload=True)
    image_sync.drop()
