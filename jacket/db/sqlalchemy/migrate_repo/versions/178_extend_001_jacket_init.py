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


def define_tables(meta):
    images_mapper = Table(
        'images_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('image_id', String(36), nullable=False),
        Column('project_id', String(255)),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('image_id_deleted_idx', 'image_id', 'deleted'),
        Index('image_id_project_id_deleted_idx', 'image_id', 'project_id',
              'deleted'),
        UniqueConstraint('image_id', 'project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    flavors_mapper = Table(
        'flavors_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('flavor_id', String(255), nullable=False),
        Column('project_id', String(255)),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('flavor_id_deleted_idx', 'flavor_id', 'deleted'),
        Index('flavor_id_az_deleted_idx', 'flavor_id', 'project_id',
              'deleted'),
        UniqueConstraint('flavor_id', 'project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    projects_mapper = Table(
        'projects_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('project_id', String(255), nullable=False),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('project_id_deleted_idx', 'project_id', 'deleted'),
        UniqueConstraint('project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    instances_mapper = Table(
        'instances_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('instance_id', String(36), nullable=False),
        Column('project_id', String(255)),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('instance_id_deleted_idx', 'instance_id', 'deleted'),
        Index('instance_id_az_deleted_idx', 'instance_id', 'project_id',
              'deleted'),
        UniqueConstraint('instance_id', 'project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    volumes_mapper = Table(
        'volumes_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('volume_id', String(36), nullable=False),
        Column('project_id', String(255)),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('volume_id_deleted_idx', 'volume_id', 'deleted'),
        Index('volume_id_az_deleted_idx', 'volume_id', 'project_id',
              'deleted'),
        UniqueConstraint('volume_id', 'project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    volume_snapshots_mapper = Table(
        'volume_snapshots_mapper', meta,
        Column('created_at', DateTime),
        Column('updated_at', DateTime),
        Column('deleted_at', DateTime),
        Column('deleted', Integer),
        Column('id', Integer, primary_key=True),
        Column('snapshot_id', String(36), nullable=False),
        Column('project_id', String(255)),
        Column('key', String(255)),
        Column('value', String(255)),
        Index('snapshot_id_deleted_idx', 'snapshot_id', 'deleted'),
        Index('snapshot_id_az_deleted_idx', 'snapshot_id', 'project_id',
              'deleted'),
        UniqueConstraint('snapshot_id', 'project_id', 'deleted', 'key'),
        mysql_engine='InnoDB',
        mysql_charset='utf8'
    )

    return [images_mapper, flavors_mapper, projects_mapper, instances_mapper,
            volumes_mapper, volume_snapshots_mapper]


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    # create all tables
    # Take care on create order for those with FK dependencies
    tables = define_tables(meta)

    for table in tables:
        table.create()

    if migrate_engine.name == "mysql":
        tables = ['images_mapper', 'flavors_mapper', 'projects_mapper']

        migrate_engine.execute("SET foreign_key_checks = 0")
        for table in tables:
            migrate_engine.execute(
                "ALTER TABLE %s CONVERT TO CHARACTER SET utf8" % table)
        migrate_engine.execute("SET foreign_key_checks = 1")
        migrate_engine.execute(
            "ALTER DATABASE %s DEFAULT CHARACTER SET utf8" %
            migrate_engine.url.database)
        migrate_engine.execute("ALTER TABLE %s Engine=InnoDB" % table)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    # drop all tables
    tables = define_tables(meta)

    for table in tables:
        table.drop()
