#    Copyright 2015 Intel Corporation
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

import mock
import six

from jacket.storage import exception
from jacket.objects import storage
from jacket.tests.storage.unit import fake_constants as fake
from jacket.objects import storage as test_objects
from jacket.tests.storage.unit.objects.test_consistencygroup import \
    fake_consistencygroup

fake_cgsnapshot = {
    'id': fake.cgsnapshot_id,
    'user_id': fake.user_id,
    'project_id': fake.project_id,
    'name': 'fake_name',
    'description': 'fake_description',
    'status': 'creating',
    'consistencygroup_id': fake.consistency_group_id,
}


class TestCGSnapshot(test_objects.BaseObjectsTestCase):

    @mock.patch('storage.db.sqlalchemy.api.cgsnapshot_get',
                return_value=fake_cgsnapshot)
    def test_get_by_id(self, cgsnapshot_get):
        cgsnapshot = storage.CGSnapshot.get_by_id(self.context,
                                                  fake.cgsnapshot_id)
        self._compare(self, fake_cgsnapshot, cgsnapshot)

    @mock.patch('storage.db.cgsnapshot_create',
                return_value=fake_cgsnapshot)
    def test_create(self, cgsnapshot_create):
        fake_cgsnap = fake_cgsnapshot.copy()
        del fake_cgsnap['id']
        cgsnapshot = storage.CGSnapshot(context=self.context, **fake_cgsnap)
        cgsnapshot.create()
        self._compare(self, fake_cgsnapshot, cgsnapshot)

    def test_create_with_id_except_exception(self):
        cgsnapshot = storage.CGSnapshot(context=self.context,
                                        **{'id': fake.consistency_group_id})
        self.assertRaises(exception.ObjectActionError, cgsnapshot.create)

    @mock.patch('storage.db.cgsnapshot_update')
    def test_save(self, cgsnapshot_update):
        cgsnapshot = storage.CGSnapshot._from_db_object(
            self.context, storage.CGSnapshot(), fake_cgsnapshot)
        cgsnapshot.status = 'active'
        cgsnapshot.save()
        cgsnapshot_update.assert_called_once_with(self.context, cgsnapshot.id,
                                                  {'status': 'active'})

    @mock.patch('storage.db.consistencygroup_update',
                return_value=fake_consistencygroup)
    @mock.patch('storage.db.cgsnapshot_update')
    def test_save_with_consistencygroup(self, cgsnapshot_update,
                                        cgsnapshot_cg_update):
        consistencygroup = storage.ConsistencyGroup._from_db_object(
            self.context, storage.ConsistencyGroup(), fake_consistencygroup)
        cgsnapshot = storage.CGSnapshot._from_db_object(
            self.context, storage.CGSnapshot(), fake_cgsnapshot)
        cgsnapshot.name = 'foobar'
        cgsnapshot.consistencygroup = consistencygroup
        self.assertEqual({'name': 'foobar',
                          'consistencygroup': consistencygroup},
                         cgsnapshot.obj_get_changes())
        self.assertRaises(exception.ObjectActionError, cgsnapshot.save)

    @mock.patch('storage.db.cgsnapshot_destroy')
    def test_destroy(self, cgsnapshot_destroy):
        cgsnapshot = storage.CGSnapshot(context=self.context,
                                        id=fake.cgsnapshot_id)
        cgsnapshot.destroy()
        self.assertTrue(cgsnapshot_destroy.called)
        admin_context = cgsnapshot_destroy.call_args[0][0]
        self.assertTrue(admin_context.is_admin)

    @mock.patch('storage.storage.consistencygroup.ConsistencyGroup.get_by_id')
    @mock.patch('storage.storage.snapshot.SnapshotList.get_all_for_cgsnapshot')
    def test_obj_load_attr(self, snapshotlist_get_for_cgs,
                           consistencygroup_get_by_id):
        cgsnapshot = storage.CGSnapshot._from_db_object(
            self.context, storage.CGSnapshot(), fake_cgsnapshot)
        # Test consistencygroup lazy-loaded field
        consistencygroup = storage.ConsistencyGroup(
            context=self.context, id=fake.consistency_group_id)
        consistencygroup_get_by_id.return_value = consistencygroup
        self.assertEqual(consistencygroup, cgsnapshot.consistencygroup)
        consistencygroup_get_by_id.assert_called_once_with(
            self.context, cgsnapshot.consistencygroup_id)
        # Test snapshots lazy-loaded field
        snapshots_objs = [storage.Snapshot(context=self.context, id=i)
                          for i in [fake.snapshot_id, fake.snapshot2_id,
                                    fake.snapshot3_id]]
        snapshots = storage.SnapshotList(context=self.context,
                                         storage=snapshots_objs)
        snapshotlist_get_for_cgs.return_value = snapshots
        self.assertEqual(snapshots, cgsnapshot.snapshots)
        snapshotlist_get_for_cgs.assert_called_once_with(
            self.context, cgsnapshot.id)

    @mock.patch('storage.db.sqlalchemy.api.cgsnapshot_get')
    def test_refresh(self, cgsnapshot_get):
        db_cgsnapshot1 = fake_cgsnapshot.copy()
        db_cgsnapshot2 = db_cgsnapshot1.copy()
        db_cgsnapshot2['description'] = 'foobar'

        # On the second cgsnapshot_get, return the CGSnapshot with an updated
        # description
        cgsnapshot_get.side_effect = [db_cgsnapshot1, db_cgsnapshot2]
        cgsnapshot = storage.CGSnapshot.get_by_id(self.context,
                                                  fake.cgsnapshot_id)
        self._compare(self, db_cgsnapshot1, cgsnapshot)

        # description was updated, so a CGSnapshot refresh should have a new
        # value for that field
        cgsnapshot.refresh()
        self._compare(self, db_cgsnapshot2, cgsnapshot)
        if six.PY3:
            call_bool = mock.call.__bool__()
        else:
            call_bool = mock.call.__nonzero__()
        cgsnapshot_get.assert_has_calls([mock.call(self.context,
                                                   fake.cgsnapshot_id),
                                         call_bool,
                                         mock.call(self.context,
                                                   fake.cgsnapshot_id)])


class TestCGSnapshotList(test_objects.BaseObjectsTestCase):
    @mock.patch('storage.db.cgsnapshot_get_all',
                return_value=[fake_cgsnapshot])
    def test_get_all(self, cgsnapshot_get_all):
        cgsnapshots = storage.CGSnapshotList.get_all(self.context)
        self.assertEqual(1, len(cgsnapshots))
        TestCGSnapshot._compare(self, fake_cgsnapshot, cgsnapshots[0])

    @mock.patch('storage.db.cgsnapshot_get_all_by_project',
                return_value=[fake_cgsnapshot])
    def test_get_all_by_project(self, cgsnapshot_get_all_by_project):
        cgsnapshots = storage.CGSnapshotList.get_all_by_project(
            self.context, self.project_id)
        self.assertEqual(1, len(cgsnapshots))
        TestCGSnapshot._compare(self, fake_cgsnapshot, cgsnapshots[0])

    @mock.patch('storage.db.cgsnapshot_get_all_by_group',
                return_value=[fake_cgsnapshot])
    def test_get_all_by_group(self, cgsnapshot_get_all_by_group):
        cgsnapshots = storage.CGSnapshotList.get_all_by_group(
            self.context, self.project_id)
        self.assertEqual(1, len(cgsnapshots))
        TestCGSnapshot._compare(self, fake_cgsnapshot, cgsnapshots[0])
