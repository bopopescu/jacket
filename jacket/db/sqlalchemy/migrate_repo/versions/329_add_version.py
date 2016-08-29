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

from sqlalchemy import Column
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table


def upgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    for table_prefix in ('', 'shadow_'):
        rpc_column = Column('rpc_current_version', String(36))
        object_current_version = Column('object_current_version', String(36))
        services = Table('%sservices' % table_prefix, meta)
        if not hasattr(services.c, 'rpc_current_version'):
            services.create_column(rpc_column)

        if not hasattr(services.c, 'object_current_version'):
            services.create_column(object_current_version)


def downgrade(migrate_engine):
    meta = MetaData()
    meta.bind = migrate_engine

    for table_prefix in ('', 'shadow_'):
        services = Table('%sservices' % table_prefix, meta)
        if hasattr(services.c, 'rpc_current_version'):
            services.c.rpc_current_version.drop()

        if hasattr(services.c, 'object_current_version'):
            services.c.object_current_version.drop()