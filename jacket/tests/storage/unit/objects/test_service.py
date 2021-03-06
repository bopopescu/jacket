#    Copyright 2015 Intel Corp.
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

from jacket.objects import storage
from jacket.tests.storage.unit import fake_service
from jacket.objects import storage as test_objects


class TestService(test_objects.BaseObjectsTestCase):

    @mock.patch('storage.db.sqlalchemy.api.service_get')
    def test_get_by_id(self, service_get):
        db_service = fake_service.fake_db_service()
        service_get.return_value = db_service
        service = storage.Service.get_by_id(self.context, 1)
        self._compare(self, db_service, service)
        service_get.assert_called_once_with(self.context, 1)

    @mock.patch('storage.db.service_get_by_host_and_topic')
    def test_get_by_host_and_topic(self, service_get_by_host_and_topic):
        db_service = fake_service.fake_db_service()
        service_get_by_host_and_topic.return_value = db_service
        service = storage.Service.get_by_host_and_topic(
            self.context, 'fake-host', 'fake-topic')
        self._compare(self, db_service, service)
        service_get_by_host_and_topic.assert_called_once_with(
            self.context, 'fake-host', 'fake-topic')

    @mock.patch('storage.db.service_get_by_args')
    def test_get_by_args(self, service_get_by_args):
        db_service = fake_service.fake_db_service()
        service_get_by_args.return_value = db_service
        service = storage.Service.get_by_args(
            self.context, 'fake-host', 'fake-key')
        self._compare(self, db_service, service)
        service_get_by_args.assert_called_once_with(
            self.context, 'fake-host', 'fake-key')

    @mock.patch('storage.db.service_create')
    def test_create(self, service_create):
        db_service = fake_service.fake_db_service()
        service_create.return_value = db_service
        service = storage.Service(context=self.context)
        service.create()
        self.assertEqual(db_service['id'], service.id)
        service_create.assert_called_once_with(self.context, {})

    @mock.patch('storage.db.service_update')
    def test_save(self, service_update):
        db_service = fake_service.fake_db_service()
        service = storage.Service._from_db_object(
            self.context, storage.Service(), db_service)
        service.topic = 'foobar'
        service.save()
        service_update.assert_called_once_with(self.context, service.id,
                                               {'topic': 'foobar'})

    @mock.patch('storage.db.service_destroy')
    def test_destroy(self, service_destroy):
        db_service = fake_service.fake_db_service()
        service = storage.Service._from_db_object(
            self.context, storage.Service(), db_service)
        with mock.patch.object(service._context, 'elevated') as elevated_ctx:
            service.destroy()
            service_destroy.assert_called_once_with(elevated_ctx(), 123)

    @mock.patch('storage.db.sqlalchemy.api.service_get')
    def test_refresh(self, service_get):
        db_service1 = fake_service.fake_db_service()
        db_service2 = db_service1.copy()
        db_service2['availability_zone'] = 'foobar'

        # On the second service_get, return the service with an updated
        # availability_zone
        service_get.side_effect = [db_service1, db_service2]
        service = storage.Service.get_by_id(self.context, 123)
        self._compare(self, db_service1, service)

        # availability_zone was updated, so a service refresh should have a
        # new value for that field
        service.refresh()
        self._compare(self, db_service2, service)
        if six.PY3:
            call_bool = mock.call.__bool__()
        else:
            call_bool = mock.call.__nonzero__()
        service_get.assert_has_calls([mock.call(self.context, 123),
                                      call_bool,
                                      mock.call(self.context, 123)])

    @mock.patch('storage.db.service_get_all_by_binary')
    def _test_get_minimum_version(self, services_update, expected,
                                  service_get_all_by_binary):
        services = [fake_service.fake_db_service(**s) for s in services_update]
        service_get_all_by_binary.return_value = services

        min_rpc = storage.Service.get_minimum_rpc_version(self.context, 'foo')
        self.assertEqual(expected[0], min_rpc)
        min_obj = storage.Service.get_minimum_obj_version(self.context, 'foo')
        self.assertEqual(expected[1], min_obj)
        service_get_all_by_binary.assert_has_calls(
            [mock.call(self.context, 'foo', disabled=None)] * 2)

    @mock.patch('storage.db.service_get_all_by_binary')
    def test_get_minimum_version(self, service_get_all_by_binary):
        services_update = [
            {'rpc_current_version': '1.0', 'object_current_version': '1.3'},
            {'rpc_current_version': '1.1', 'object_current_version': '1.2'},
            {'rpc_current_version': '2.0', 'object_current_version': '2.5'},
        ]
        expected = ('1.0', '1.2')
        self._test_get_minimum_version(services_update, expected)

    @mock.patch('storage.db.service_get_all_by_binary')
    def test_get_minimum_version_liberty(self, service_get_all_by_binary):
        services_update = [
            {'rpc_current_version': '1.0', 'object_current_version': '1.3'},
            {'rpc_current_version': '1.1', 'object_current_version': None},
            {'rpc_current_version': None, 'object_current_version': '2.5'},
        ]
        expected = ('liberty', 'liberty')
        self._test_get_minimum_version(services_update, expected)


class TestServiceList(test_objects.BaseObjectsTestCase):
    @mock.patch('storage.db.service_get_all')
    def test_get_all(self, service_get_all):
        db_service = fake_service.fake_db_service()
        service_get_all.return_value = [db_service]

        filters = {'host': 'host', 'binary': 'foo', 'disabled': False}
        services = storage.ServiceList.get_all(self.context, filters)
        service_get_all.assert_called_once_with(self.context, filters)
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])

    @mock.patch('storage.db.service_get_all_by_topic')
    def test_get_all_by_topic(self, service_get_all_by_topic):
        db_service = fake_service.fake_db_service()
        service_get_all_by_topic.return_value = [db_service]

        services = storage.ServiceList.get_all_by_topic(
            self.context, 'foo', 'bar')
        service_get_all_by_topic.assert_called_once_with(
            self.context, 'foo', disabled='bar')
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])

    @mock.patch('storage.db.service_get_all_by_binary')
    def test_get_all_by_binary(self, service_get_all_by_binary):
        db_service = fake_service.fake_db_service()
        service_get_all_by_binary.return_value = [db_service]

        services = storage.ServiceList.get_all_by_binary(
            self.context, 'foo', 'bar')
        service_get_all_by_binary.assert_called_once_with(
            self.context, 'foo', disabled='bar')
        self.assertEqual(1, len(services))
        TestService._compare(self, db_service, services[0])
