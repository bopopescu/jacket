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
from jacket.compute.scheduler.filters import retry_filter
from jacket.compute import test
from jacket.tests.compute.unit.scheduler import fakes


class TestRetryFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestRetryFilter, self).setUp()
        self.filt_cls = retry_filter.RetryFilter()

    def test_retry_filter_disabled(self):
        # Test case where retry/re-scheduling is disabled.
        host = fakes.FakeHostState('host1', 'node1', {})
        spec_obj = compute.RequestSpec(retry=None)
        self.assertTrue(self.filt_cls.host_passes(host, spec_obj))

    def test_retry_filter_pass(self):
        # Node not previously tried.
        host = fakes.FakeHostState('host1', 'nodeX', {})
        retry = compute.SchedulerRetries(
            num_attempts=2,
            hosts=compute.ComputeNodeList(compute=[
                # same host, different node
                compute.ComputeNode(host='host1', hypervisor_hostname='node1'),
                # different host and node
                compute.ComputeNode(host='host2', hypervisor_hostname='node2'),
            ]))
        spec_obj = compute.RequestSpec(retry=retry)
        self.assertTrue(self.filt_cls.host_passes(host, spec_obj))

    def test_retry_filter_fail(self):
        # Node was already tried.
        host = fakes.FakeHostState('host1', 'node1', {})
        retry = compute.SchedulerRetries(
            num_attempts=1,
            hosts=compute.ComputeNodeList(compute=[
                compute.ComputeNode(host='host1', hypervisor_hostname='node1')
            ]))
        spec_obj = compute.RequestSpec(retry=retry)
        self.assertFalse(self.filt_cls.host_passes(host, spec_obj))
