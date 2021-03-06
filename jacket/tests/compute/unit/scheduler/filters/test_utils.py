# Copyright 2015 IBM Corp.
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

from jacket.objects import compute
from jacket.compute.scheduler.filters import utils
from jacket.compute import test
from jacket.tests.compute.unit.scheduler import fakes

_AGGREGATE_FIXTURES = [
    compute.Aggregate(
        id=1,
        name='foo',
        hosts=['fake-host'],
        metadata={'k1': '1', 'k2': '2'},
    ),
    compute.Aggregate(
        id=2,
        name='bar',
        hosts=['fake-host'],
        metadata={'k1': '3', 'k2': '4'},
    ),
    compute.Aggregate(
        id=3,
        name='bar',
        hosts=['fake-host'],
        metadata={'k1': '6,7', 'k2': '8, 9'},
    ),
]


class TestUtils(test.NoDBTestCase):
    def setUp(self):
        super(TestUtils, self).setUp()

    def test_aggregate_values_from_key(self):
        host_state = fakes.FakeHostState(
            'fake', 'node', {'aggregates': _AGGREGATE_FIXTURES})

        values = utils.aggregate_values_from_key(host_state, key_name='k1')

        self.assertEqual(set(['1', '3', '6,7']), values)

    def test_aggregate_values_from_key_with_wrong_key(self):
        host_state = fakes.FakeHostState(
            'fake', 'node', {'aggregates': _AGGREGATE_FIXTURES})

        values = utils.aggregate_values_from_key(host_state, key_name='k3')

        self.assertEqual(set(), values)

    def test_aggregate_metadata_get_by_host_no_key(self):
        host_state = fakes.FakeHostState(
            'fake', 'node', {'aggregates': _AGGREGATE_FIXTURES})

        metadata = utils.aggregate_metadata_get_by_host(host_state)

        self.assertIn('k1', metadata)
        self.assertEqual(set(['1', '3', '7', '6']), metadata['k1'])
        self.assertIn('k2', metadata)
        self.assertEqual(set(['9', '8', '2', '4']), metadata['k2'])

    def test_aggregate_metadata_get_by_host_with_key(self):
        host_state = fakes.FakeHostState(
            'fake', 'node', {'aggregates': _AGGREGATE_FIXTURES})

        metadata = utils.aggregate_metadata_get_by_host(host_state, 'k1')

        self.assertIn('k1', metadata)
        self.assertEqual(set(['1', '3', '7', '6']), metadata['k1'])

    def test_aggregate_metadata_get_by_host_empty_result(self):
        host_state = fakes.FakeHostState(
            'fake', 'node', {'aggregates': []})

        metadata = utils.aggregate_metadata_get_by_host(host_state, 'k3')

        self.assertEqual({}, metadata)

    def test_validate_num_values(self):
        f = utils.validate_num_values

        self.assertEqual("x", f(set(), default="x"))
        self.assertEqual(1, f(set(["1"]), cast_to=int))
        self.assertEqual(1.0, f(set(["1"]), cast_to=float))
        self.assertEqual(1, f(set([1, 2]), based_on=min))
        self.assertEqual(2, f(set([1, 2]), based_on=max))
        self.assertEqual(9, f(set(['10', '9']), based_on=min))

    def test_instance_uuids_overlap(self):
        inst1 = compute.Instance(uuid='aa')
        inst2 = compute.Instance(uuid='bb')
        instances = [inst1, inst2]
        host_state = fakes.FakeHostState('host1', 'node1', {})
        host_state.instances = {instance.uuid: instance
                                for instance in instances}
        self.assertTrue(utils.instance_uuids_overlap(host_state, ['aa']))
        self.assertFalse(utils.instance_uuids_overlap(host_state, ['zz']))

    def test_other_types_on_host(self):
        inst1 = compute.Instance(uuid='aa', instance_type_id=1)
        host_state = fakes.FakeHostState('host1', 'node1', {})
        host_state.instances = {inst1.uuid: inst1}
        self.assertFalse(utils.other_types_on_host(host_state, 1))
        self.assertTrue(utils.other_types_on_host(host_state, 2))
