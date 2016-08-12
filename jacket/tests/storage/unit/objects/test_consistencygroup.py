# Copyright 2015 Yahoo Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import six

from jacket.storage import exception
from jacket.objects import storage
from jacket.objects.storage import fields
from jacket.tests.storage.unit import fake_constants as fake
from jacket.objects import storage as test_objects

fake_consistencygroup = {
    'id': fake.consistency_group_id,
    'user_id': fake.user_id,
    'project_id': fake.project_id,
    'host': 'fake_host',
    'availability_zone': 'fake_az',
    'name': 'fake_name',
    'description': 'fake_description',
    'volume_type_id': fake.volume_type_id,
    'status': fields.ConsistencyGroupStatus.CREATING,
    'cgsnapshot_id': fake.cgsnapshot_id,
    'source_cgid': None,
}

fake_cgsnapshot = {
    'id': fake.cgsnapshot_id,
    'user_id': fake.user_id,
    'project_id': fake.project_id,
    'name': 'fake_name',
    'description': 'fake_description',
    'status': 'creating',
    'consistencygroup_id': fake.consistency_group_id,
}


class TestConsistencyGroup(test_objects.BaseObjectsTestCase):

    @mock.patch('storage.db.sqlalchemy.api.consistencygroup_get',
                return_value=fake_consistencygroup)
    def test_get_by_id(self, consistencygroup_get):
        consistencygroup = storage.ConsistencyGroup.get_by_id(
            self.context, fake.consistency_group_id)
        self._compare(self, fake_consistencygroup, consistencygroup)
        consistencygroup_get.assert_called_once_with(
            self.context, fake.consistency_group_id)

    @mock.patch('storage.db.sqlalchemy.api.model_query')
    def test_get_by_id_no_existing_id(self, model_query):
        model_query().filter_by().first.return_value = None
        self.assertRaises(exception.ConsistencyGroupNotFound,
                          storage.ConsistencyGroup.get_by_id, self.context,
                          123)

    @mock.patch('storage.db.consistencygroup_create',
                return_value=fake_consistencygroup)
    def test_create(self, consistencygroup_create):
        fake_cg = fake_consistencygroup.copy()
        del fake_cg['id']
        consistencygroup = storage.ConsistencyGroup(context=self.context,
                                                    **fake_cg)
        consistencygroup.create()
        self._compare(self, fake_consistencygroup, consistencygroup)

    def test_create_with_id_except_exception(self, ):
        consistencygroup = storage.ConsistencyGroup(
            context=self.context, **{'id': fake.consistency_group_id})
        self.assertRaises(exception.ObjectActionError, consistencygroup.create)

    @mock.patch('storage.db.consistencygroup_update')
    def test_save(self, consistencygroup_update):
        consistencygroup = storage.ConsistencyGroup._from_db_object(
            self.context, storage.ConsistencyGroup(), fake_consistencygroup)
        consistencygroup.status = fields.ConsistencyGroupStatus.AVAILABLE
        consistencygroup.save()
        consistencygroup_update.assert_called_once_with(
            self.context,
            consistencygroup.id,
            {'status': fields.ConsistencyGroupStatus.AVAILABLE})

    def test_save_with_cgsnapshots(self):
        consistencygroup = storage.ConsistencyGroup._from_db_object(
            self.context, storage.ConsistencyGroup(), fake_consistencygroup)
        cgsnapshots_objs = [storage.CGSnapshot(context=self.context, id=i)
                            for i in [fake.cgsnapshot_id, fake.cgsnapshot2_id,
                                      fake.cgsnapshot3_id]]
        cgsnapshots = storage.CGSnapshotList(storage=cgsnapshots_objs)
        consistencygroup.name = 'foobar'
        consistencygroup.cgsnapshots = cgsnapshots
        self.assertEqual({'name': 'foobar',
                          'cgsnapshots': cgsnapshots},
                         consistencygroup.obj_get_changes())
        self.assertRaises(exception.ObjectActionError, consistencygroup.save)

    def test_save_with_volumes(self):
        consistencygroup = storage.ConsistencyGroup._from_db_object(
            self.context, storage.ConsistencyGroup(), fake_consistencygroup)
        volumes_objs = [storage.Volume(context=self.context, id=i)
                        for i in [fake.volume_id, fake.volume2_id,
                                  fake.volume3_id]]
        volumes = storage.VolumeList(storage=volumes_objs)
        consistencygroup.name = 'foobar'
        consistencygroup.volumes = volumes
        self.assertEqual({'name': 'foobar',
                          'volumes': volumes},
                         consistencygroup.obj_get_changes())
        self.assertRaises(exception.ObjectActionError, consistencygroup.save)

    @mock.patch('storage.storage.cgsnapshot.CGSnapshotList.get_all_by_group')
    @mock.patch('storage.storage.volume.VolumeList.get_all_by_group')
    def test_obj_load_attr(self, mock_vol_get_all_by_group,
                           mock_cgsnap_get_all_by_group):
        consistencygroup = storage.ConsistencyGroup._from_db_object(
            self.context, storage.ConsistencyGroup(), fake_consistencygroup)
        # Test cgsnapshots lazy-loaded field
        cgsnapshots_objs = [storage.CGSnapshot(context=self.context, id=i)
                            for i in [fake.cgsnapshot_id, fake.cgsnapshot2_id,
                                      fake.cgsnapshot3_id]]
        cgsnapshots = storage.CGSnapshotList(context=self.context,
                                             storage=cgsnapshots_objs)
        mock_cgsnap_get_all_by_group.return_value = cgsnapshots
        self.assertEqual(cgsnapshots, consistencygroup.cgsnapshots)
        mock_cgsnap_get_all_by_group.assert_called_once_with(
            self.context, consistencygroup.id)

        # Test volumes lazy-loaded field
        volume_objs = [storage.Volume(context=self.context, id=i)
                       for i in [fake.volume_id, fake.volume2_id,
                                 fake.volume3_id]]
        volumes = storage.VolumeList(context=self.context, storage=volume_objs)
        mock_vol_get_all_by_group.return_value = volumes
        self.assertEqual(volumes, consistencygroup.volumes)
        mock_vol_get_all_by_group.assert_called_once_with(self.context,
                                                          consistencygroup.id)

    @mock.patch('storage.db.consistencygroup_destroy')
    def test_destroy(self, consistencygroup_destroy):
        consistencygroup = storage.ConsistencyGroup(
            context=self.context, id=fake.consistency_group_id)
        consistencygroup.destroy()
        self.assertTrue(consistencygroup_destroy.called)
        admin_context = consistencygroup_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    @mock.patch('storage.db.sqlalchemy.api.consistencygroup_get')
    def test_refresh(self, consistencygroup_get):
        db_cg1 = fake_consistencygroup.copy()
        db_cg2 = db_cg1.copy()
        db_cg2['description'] = 'foobar'

        # On the second consistencygroup_get, return the ConsistencyGroup with
        # an updated description
        consistencygroup_get.side_effect = [db_cg1, db_cg2]
        cg = storage.ConsistencyGroup.get_by_id(self.context,
                                                fake.consistency_group_id)
        self._compare(self, db_cg1, cg)

        # description was updated, so a ConsistencyGroup refresh should have a
        # new value for that field
        cg.refresh()
        self._compare(self, db_cg2, cg)
        if six.PY3:
            call_bool = mock.call.__bool__()
        else:
            call_bool = mock.call.__nonzero__()
        consistencygroup_get.assert_has_calls([
            mock.call(
                self.context,
                fake.consistency_group_id),
            call_bool,
            mock.call(
                self.context,
                fake.consistency_group_id)])


class TestConsistencyGroupList(test_objects.BaseObjectsTestCase):
    @mock.patch('storage.db.consistencygroup_get_all',
                return_value=[fake_consistencygroup])
    def test_get_all(self, consistencygroup_get_all):
        consistencygroups = storage.ConsistencyGroupList.get_all(self.context)
        self.assertEqual(1, len(consistencygroups))
        TestConsistencyGroup._compare(self, fake_consistencygroup,
                                      consistencygroups[0])

    @mock.patch('storage.db.consistencygroup_get_all_by_project',
                return_value=[fake_consistencygroup])
    def test_get_all_by_project(self, consistencygroup_get_all_by_project):
        consistencygroups = storage.ConsistencyGroupList.get_all_by_project(
            self.context, self.project_id)
        self.assertEqual(1, len(consistencygroups))
        TestConsistencyGroup._compare(self, fake_consistencygroup,
                                      consistencygroups[0])

    @mock.patch('storage.db.consistencygroup_get_all',
                return_value=[fake_consistencygroup])
    def test_get_all_with_pagination(self, consistencygroup_get_all):
        consistencygroups = storage.ConsistencyGroupList.get_all(
            self.context, filters={'id': 'fake'}, marker=None, limit=1,
            offset=None, sort_keys='id', sort_dirs='asc')
        self.assertEqual(1, len(consistencygroups))
        consistencygroup_get_all.assert_called_once_with(
            self.context, filters={'id': 'fake'}, marker=None, limit=1,
            offset=None, sort_keys='id', sort_dirs='asc')
        TestConsistencyGroup._compare(self, fake_consistencygroup,
                                      consistencygroups[0])

    @mock.patch('storage.db.consistencygroup_get_all_by_project',
                return_value=[fake_consistencygroup])
    def test_get_all_by_project_with_pagination(
            self, consistencygroup_get_all_by_project):
        consistencygroups = storage.ConsistencyGroupList.get_all_by_project(
            self.context, self.project_id, filters={'id': 'fake'}, marker=None,
            limit=1, offset=None, sort_keys='id', sort_dirs='asc')
        self.assertEqual(1, len(consistencygroups))
        consistencygroup_get_all_by_project.assert_called_once_with(
            self.context, self.project_id, filters={'id': 'fake'}, marker=None,
            limit=1, offset=None, sort_keys='id', sort_dirs='asc')
        TestConsistencyGroup._compare(self, fake_consistencygroup,
                                      consistencygroups[0])
