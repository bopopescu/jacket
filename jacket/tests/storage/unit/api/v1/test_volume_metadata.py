# Copyright 2011 OpenStack Foundation
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

import uuid

import mock
from oslo_config import cfg
from oslo_serialization import jsonutils
import webob

from jacket.api.storage.storage import extensions
from jacket.api.storage.storage.v1 import volume_metadata
from jacket.api.storage.storage.v1 import volumes
import jacket.db.storage
from jacket.storage import exception
from jacket.storage import test
from jacket.tests.storage.unit.api import fakes
from jacket.tests.storage.unit.api.v1 import stubs
from jacket.tests.storage.unit import fake_volume
from jacket.storage import volume


CONF = cfg.CONF


def return_create_volume_metadata_max(context, volume_id, metadata, delete):
    return stub_max_volume_metadata()


def return_create_volume_metadata(context, volume_id, metadata, delete,
                                  meta_type):
    return stub_volume_metadata()


def return_new_volume_metadata(context, volume_id, metadata,
                               delete, meta_type):
    return stub_new_volume_metadata()


def return_create_volume_metadata_insensitive(context, snapshot_id,
                                              metadata, delete,
                                              meta_type):
    return stub_volume_metadata_insensitive()


def return_volume_metadata(context, volume_id):
    return stub_volume_metadata()


def return_empty_volume_metadata(context, volume_id):
    return {}


def return_empty_container_metadata(context, volume_id, metadata,
                                    delete, meta_type):
    return {}


def delete_volume_metadata(context, volume_id, key, meta_type):
    pass


def stub_volume_metadata():
    metadata = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3",
    }
    return metadata


def stub_new_volume_metadata():
    metadata = {
        'key10': 'value10',
        'key99': 'value99',
        'KEY20': 'value20',
    }
    return metadata


def stub_volume_metadata_insensitive():
    metadata = {
        "key1": "value1",
        "key2": "value2",
        "key3": "value3",
        "KEY4": "value4",
    }
    return metadata


def stub_max_volume_metadata():
    metadata = {"metadata": {}}
    for num in range(CONF.quota_metadata_items):
        metadata['metadata']['key%i' % num] = "blah"
    return metadata


def get_volume(*args, **kwargs):
    vol = {'id': args[1],
           'size': 100,
           'name': 'fake',
           'host': 'fake-host',
           'status': 'available',
           'encryption_key_id': None,
           'volume_type_id': None,
           'migration_status': None,
           'availability_zone': 'zone1:host1',
           'attach_status': 'detached'}
    return fake_volume.fake_volume_obj(args[0], **vol)


def return_volume_nonexistent(*args, **kwargs):
    raise exception.VolumeNotFound('bogus test message')


def fake_update_volume_metadata(self, context, volume, diff):
    pass


class volumeMetaDataTest(test.TestCase):

    def setUp(self):
        super(volumeMetaDataTest, self).setUp()
        self.volume_api = jacket.storage.volume.api.API()
        self.stubs.Set(volume.api.API, 'get', get_volume)
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_volume_metadata)
        self.stubs.Set(jacket.db.storage, 'service_get_all_by_topic',
                       stubs.stub_service_get_all_by_topic)

        self.stubs.Set(self.volume_api, 'update_volume_metadata',
                       fake_update_volume_metadata)

        self.ext_mgr = extensions.ExtensionManager()
        self.ext_mgr.extensions = {}
        self.volume_controller = volumes.VolumeController(self.ext_mgr)
        self.controller = volume_metadata.Controller()
        self.req_id = str(uuid.uuid4())
        self.url = '/v1/fake/volumes/%s/metadata' % self.req_id

        vol = {"size": 100,
               "display_name": "Volume Test Name",
               "display_description": "Volume Test Desc",
               "availability_zone": "zone1:host1",
               "metadata": {}}
        body = {"volume": vol}
        req = fakes.HTTPRequest.blank('/v1/volumes')
        self.volume_controller.create(req, body)

    def test_index(self):
        req = fakes.HTTPRequest.blank(self.url)
        res_dict = self.controller.index(req, self.req_id)

        expected = {
            'metadata': {
                'key1': 'value1',
                'key2': 'value2',
                'key3': 'value3',
            },
        }
        self.assertEqual(expected, res_dict)

    def test_index_nonexistent_volume(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_volume_nonexistent)
        req = fakes.HTTPRequest.blank(self.url)
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.index, req, self.url)

    def test_index_no_data(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_empty_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url)
        res_dict = self.controller.index(req, self.req_id)
        expected = {'metadata': {}}
        self.assertEqual(expected, res_dict)

    def test_show(self):
        req = fakes.HTTPRequest.blank(self.url + '/key2')
        res_dict = self.controller.show(req, self.req_id, 'key2')
        expected = {'meta': {'key2': 'value2'}}
        self.assertEqual(expected, res_dict)

    def test_show_nonexistent_volume(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_volume_nonexistent)
        req = fakes.HTTPRequest.blank(self.url + '/key2')
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.show, req, self.req_id, 'key2')

    def test_show_meta_not_found(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_empty_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key6')
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.show, req, self.req_id, 'key6')

    @mock.patch.object(jacket.db.storage, 'volume_metadata_delete')
    @mock.patch.object(jacket.db.storage, 'volume_metadata_get')
    def test_delete(self, metadata_get, metadata_delete):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_get.side_effect = return_volume_metadata
        metadata_delete.side_effect = delete_volume_metadata
        req = fakes.HTTPRequest.blank(self.url + '/key2')
        req.method = 'DELETE'
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res = self.controller.delete(req, self.req_id, 'key2')
            self.assertEqual(200, res.status_int)
            get_volume.assert_called_with(fake_context, self.req_id)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_delete')
    @mock.patch.object(jacket.db.storage, 'volume_metadata_get')
    def test_delete_nonexistent_volume(self, metadata_get, metadata_delete):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_get.side_effect = return_volume_metadata
        metadata_delete.side_effect = return_volume_nonexistent
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'DELETE'
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPNotFound,
                              self.controller.delete, req,
                              self.req_id, 'key1')
            get_volume.assert_called_with(fake_context, self.req_id)

    def test_delete_meta_not_found(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_empty_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key6')
        req.method = 'DELETE'
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.delete, req, self.req_id, 'key6')

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    @mock.patch.object(jacket.db.storage, 'volume_metadata_get')
    def test_create(self, metadata_get, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_get.side_effect = return_empty_volume_metadata
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank('/v2/volume_metadata')
        req.method = 'POST'
        req.content_type = "application/json"
        body = {"metadata": {"key1": "value1",
                             "key2": "value2",
                             "key3": "value3", }}
        req.body = jsonutils.dump_as_bytes(body)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.create(req, self.req_id, body)
            self.assertEqual(body, res_dict)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    @mock.patch.object(jacket.db.storage, 'volume_metadata_get')
    def test_create_with_keys_in_uppercase_and_lowercase(self, metadata_get,
                                                         metadata_update):
        # if the keys in uppercase_and_lowercase, should return the one
        # which server added
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_get.side_effect = return_empty_volume_metadata
        metadata_update.side_effect = return_create_volume_metadata_insensitive

        req = fakes.HTTPRequest.blank('/v2/volume_metadata')
        req.method = 'POST'
        req.content_type = "application/json"
        body = {"metadata": {"key1": "value1",
                             "KEY1": "value1",
                             "key2": "value2",
                             "KEY2": "value2",
                             "key3": "value3",
                             "KEY4": "value4"}}
        expected = {"metadata": {"key1": "value1",
                                 "key2": "value2",
                                 "key3": "value3",
                                 "KEY4": "value4"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.create(req, self.req_id, body)
            self.assertEqual(expected, res_dict)

    def test_create_empty_body(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'POST'
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.create, req, self.req_id, None)

    def test_create_item_empty_key(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {"": "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.create, req, self.req_id, body)

    def test_create_item_key_too_long(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {("a" * 260): "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.create,
                          req, self.req_id, body)

    def test_create_nonexistent_volume(self):
        self.stubs.Set(volume.api.API, 'get', return_volume_nonexistent)
        self.stubs.Set(jacket.db.storage, 'volume_metadata_get',
                       return_volume_metadata)
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)

        req = fakes.HTTPRequest.blank('/v1/volume_metadata')
        req.method = 'POST'
        req.content_type = "application/json"
        body = {"metadata": {"key9": "value9"}}
        req.body = jsonutils.dump_as_bytes(body)
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.create, req, self.req_id, body)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_all(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_new_volume_metadata
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        expected = {
            'metadata': {
                'key10': 'value10',
                'key99': 'value99',
                'KEY20': 'value20',
            },
        }
        req.body = jsonutils.dump_as_bytes(expected)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.update_all(req, self.req_id, expected)
            self.assertEqual(expected, res_dict)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    @mock.patch.object(jacket.db.storage, 'volume_metadata_get')
    def test_update_all_with_keys_in_uppercase_and_lowercase(self,
                                                             metadata_get,
                                                             metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_get.side_effect = return_create_volume_metadata
        metadata_update.side_effect = return_new_volume_metadata
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        body = {
            'metadata': {
                'key10': 'value10',
                'KEY10': 'value10',
                'key99': 'value99',
                'KEY20': 'value20',
            },
        }
        expected = {
            'metadata': {
                'key10': 'value10',
                'key99': 'value99',
                'KEY20': 'value20',
            },
        }
        req.body = jsonutils.dump_as_bytes(expected)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.update_all(req, self.req_id, body)
            self.assertEqual(expected, res_dict)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_all_empty_container(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_empty_container_metadata
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        expected = {'metadata': {}}
        req.body = jsonutils.dump_as_bytes(expected)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.update_all(req, self.req_id, expected)
            self.assertEqual(expected, res_dict)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_item_value_too_long(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {"key1": ("a" * 260)}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPRequestEntityTooLarge,
                              self.controller.update,
                              req, self.req_id, "key1", body)
            self.assertFalse(metadata_update.called)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    def test_update_all_malformed_container(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        expected = {'meta': {}}
        req.body = jsonutils.dump_as_bytes(expected)

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update_all, req, self.req_id,
                          expected)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_all_malformed_data(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        expected = {'metadata': ['asdf']}
        req.body = jsonutils.dump_as_bytes(expected)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.controller.update_all, req, self.req_id,
                              expected)

    def test_update_all_nonexistent_volume(self):
        self.stubs.Set(jacket.db.storage, 'volume_get', return_volume_nonexistent)
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'PUT'
        req.content_type = "application/json"
        body = {'metadata': {'key10': 'value10'}}
        req.body = jsonutils.dump_as_bytes(body)

        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.update_all, req, '100', body)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_item(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {"key1": "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            res_dict = self.controller.update(req, self.req_id, 'key1', body)
            expected = {'meta': {'key1': 'value1'}}
            self.assertEqual(expected, res_dict)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    def test_update_item_nonexistent_volume(self):
        self.stubs.Set(jacket.db.storage, 'volume_get',
                       return_volume_nonexistent)
        req = fakes.HTTPRequest.blank('/v1.1/fake/volumes/asdf/metadata/key1')
        req.method = 'PUT'
        body = {"meta": {"key1": "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller.update, req, self.req_id, 'key1',
                          body)

    def test_update_item_empty_body(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update, req, self.req_id, 'key1',
                          None)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_item_empty_key(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {"": "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.controller.update, req, self.req_id,
                              '', body)
            self.assertFalse(metadata_update.called)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_update_item_key_too_long(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {("a" * 260): "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPRequestEntityTooLarge,
                              self.controller.update,
                              req, self.req_id, ("a" * 260), body)
            self.assertFalse(metadata_update.called)
            get_volume.assert_called_once_with(fake_context, self.req_id)

    def test_update_item_too_many_keys(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/key1')
        req.method = 'PUT'
        body = {"meta": {"key1": "value1", "key2": "value2"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update, req, self.req_id, 'key1',
                          body)

    def test_update_item_body_uri_mismatch(self):
        self.stubs.Set(jacket.db.storage, 'volume_metadata_update',
                       return_create_volume_metadata)
        req = fakes.HTTPRequest.blank(self.url + '/bad')
        req.method = 'PUT'
        body = {"meta": {"key1": "value1"}}
        req.body = jsonutils.dump_as_bytes(body)
        req.headers["content-type"] = "application/json"

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller.update, req, self.req_id, 'bad',
                          body)

    @mock.patch.object(jacket.db.storage, 'volume_metadata_update')
    def test_invalid_metadata_items_on_create(self, metadata_update):
        fake_volume = {'id': self.req_id, 'status': 'available'}
        fake_context = mock.Mock()
        metadata_update.side_effect = return_create_volume_metadata
        req = fakes.HTTPRequest.blank(self.url)
        req.method = 'POST'
        req.headers["content-type"] = "application/json"

        # test for long key
        data = {"metadata": {"a" * 260: "value1"}}
        req.body = jsonutils.dump_as_bytes(data)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPRequestEntityTooLarge,
                              self.controller.create, req, self.req_id, data)

        # test for long value
        data = {"metadata": {"key": "v" * 260}}
        req.body = jsonutils.dump_as_bytes(data)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPRequestEntityTooLarge,
                              self.controller.create, req, self.req_id, data)

        # test for empty key.
        data = {"metadata": {"": "value1"}}
        req.body = jsonutils.dump_as_bytes(data)
        req.environ['storage.context'] = fake_context

        with mock.patch.object(self.controller.volume_api,
                               'get') as get_volume:
            get_volume.return_value = fake_volume
            self.assertRaises(webob.exc.HTTPBadRequest,
                              self.controller.create, req, self.req_id, data)
