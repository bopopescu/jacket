# Copyright (c) 2011 X.commerce, a business unit of eBay Inc.
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Piston Cloud Computing, Inc.
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

"""
SQLAlchemy models for jacket data.
"""

from oslo_config import cfg
from oslo_db.sqlalchemy import models
from oslo_utils import timeutils
from sqlalchemy import and_, func, select
from sqlalchemy import bindparam
from sqlalchemy import Column, Index, Integer, String, Text, schema
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import backref, column_property, relationship, validates


CONF = cfg.CONF
BASE = declarative_base()


class JacketBase(models.TimestampMixin,
                 models.ModelBase):
    """Base class for Jacket Models."""

    __table_args__ = {'mysql_engine': 'InnoDB'}

    # TODO(rpodolyaka): reuse models.SoftDeleteMixin in the next stage
    #                   of implementing of BP db-cleanup
    deleted_at = Column(DateTime)
    deleted = Column(Boolean, default=False)
    metadata = None

    @staticmethod
    def delete_values():
        return {'deleted': True,
                'deleted_at': timeutils.utcnow()}

    def delete(self, session):
        """Delete this object."""
        updated_values = self.delete_values()
        self.update(updated_values)
        self.save(session=session)
        return updated_values


class ImagesMapper(BASE, JacketBase, models.SoftDeleteMixin):
    """Represents a mapper key/value pair for images"""

    __tablename__ = "images_mapper"

    __table_args__ = (
        Index('image_id_deleted_idx', 'image_id', 'deleted'),
        Index('image_id_project_id_deleted_idx', 'image_id', 'project_id', 'deleted'),
    )

    id = Column(Integer, primary_key=True)
    image_id = Column(String(36), nullable=False)
    dest_image_id = Column(String(36), nullable=False)
    project_id = Column(String(255))
    key = Column(String(255))
    value = Column(String(255))


class FlavorsMapper(BASE, JacketBase, models.SoftDeleteMixin):
    """Represents a mapper key/value pair for flavor"""

    __tablename__ = "flavors_mapper"

    __table_args__ = (
        Index('flavor_id_deleted_idx', 'flavor_id', 'deleted'),
        Index('flavor_id_az_deleted_idx', 'flavor_id', 'project_id', 'deleted'),
    )

    id = Column(Integer, primary_key=True)
    flavor_id = Column(String(255), nullable=False)
    dest_flavor_id = Column(String(255), nullable=False)
    project_id = Column(String(255))
    key = Column(String(255))
    value = Column(String(255))


class ProjectsMapper(BASE, JacketBase, models.SoftDeleteMixin):
    """Represents a mapper key/value pair for flavor"""

    __tablename__ = "projects_mapper"

    __table_args__ = (
        Index('project_id_deleted_idx', 'project_id', 'deleted'),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(String(255), nullable=False)
    key = Column(String(255))
    value = Column(String(255))