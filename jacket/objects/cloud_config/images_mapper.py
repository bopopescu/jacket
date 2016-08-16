#    Copyright 2014 Red Hat, Inc
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

from jacket.db import cloud_config
from jacket import exception
from jacket.objects import cloud_config
from jacket.objects.cloud_config import base
from jacket.objects.cloud_config import fields


@base.JacketObjectRegistry.register
class ImagesMapper(base.NovaPersistentObject, base.NovaObject):
    VERSION = '1.0'

    fields = {
        'id': fields.IntegerField(read_only=True),
        'image_id': fields.StringField(),
        'project_id': fields.StringField(),
        'key': fields.StringField(),
        'value': fields.StringField(),
        }

    @staticmethod
    def _from_db_object(context, agent, db_agent):
        for name in agent.fields:
            setattr(agent, name, db_agent[name])
        agent._context = context
        agent.obj_reset_changes()
        return agent

    @base.remotable_classmethod
    def get_by_triple(cls, context, hypervisor, os, architecture):
        db_agent = compute.agent_build_get_by_triple(context, hypervisor,
                                                os, architecture)
        if not db_agent:
            return None
        return cls._from_db_object(context, compute.Agent(), db_agent)

    @base.remotable
    def create(self):
        updates = self.obj_get_changes()
        if 'id' in updates:
            raise exception.ObjectActionError(action='create',
                                              reason='Already Created')
        db_agent = compute.agent_build_create(self._context, updates)
        self._from_db_object(self._context, self, db_agent)

    @base.remotable
    def destroy(self):
        compute.agent_build_destroy(self._context, self.id)

    @base.remotable
    def save(self):
        updates = self.obj_get_changes()
        compute.agent_build_update(self._context, self.id, updates)
        self.obj_reset_changes()


@base.NovaObjectRegistry.register
class AgentList(base.ObjectListBase, base.NovaObject):
    VERSION = '1.0'

    fields = {
        'compute': fields.ListOfObjectsField('Agent'),
        }

    @base.remotable_classmethod
    def get_all(cls, context, hypervisor=None):
        db_agents = compute.agent_build_get_all(context, hypervisor=hypervisor)
        return base.obj_make_list(context, cls(), compute.Agent, db_agents)