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

import six

from jacket.objects import compute
from jacket.compute.scheduler.filters import compute_capabilities_filter
from jacket.compute import test
from jacket.tests.compute.unit.scheduler import fakes


class TestComputeCapabilitiesFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestComputeCapabilitiesFilter, self).setUp()
        self.filt_cls = compute_capabilities_filter.ComputeCapabilitiesFilter()

    def _do_test_compute_filter_extra_specs(self, ecaps, especs, passes):
        # In real OpenStack runtime environment,compute capabilities
        # value may be number, so we should use number to do unit test.
        capabilities = {}
        capabilities.update(ecaps)
        spec_obj = compute.RequestSpec(
            flavor=compute.Flavor(memory_mb=1024, extra_specs=especs))
        host_state = {'free_ram_mb': 1024}
        host_state.update(capabilities)
        host = fakes.FakeHostState('host1', 'node1', host_state)
        assertion = self.assertTrue if passes else self.assertFalse
        assertion(self.filt_cls.host_passes(host, spec_obj))

    def test_compute_filter_passes_without_extra_specs(self):
        spec_obj = compute.RequestSpec(
            flavor=compute.Flavor(memory_mb=1024))
        host_state = {'free_ram_mb': 1024}
        host = fakes.FakeHostState('host1', 'node1', host_state)
        self.assertTrue(self.filt_cls.host_passes(host, spec_obj))

    def test_compute_filter_fails_without_host_state(self):
        especs = {'capabilities': '1'}
        spec_obj = compute.RequestSpec(
            flavor=compute.Flavor(memory_mb=1024, extra_specs=especs))
        self.assertFalse(self.filt_cls.host_passes(None, spec_obj))

    def test_compute_filter_fails_without_capabilites(self):
        cpu_info = """ { } """

        cpu_info = six.text_type(cpu_info)

        self._do_test_compute_filter_extra_specs(
            ecaps={'cpu_info': cpu_info},
            especs={'capabilities:cpu_info:vendor': 'Intel'},
            passes=False)

    def test_compute_filter_pass_cpu_info_as_text_type(self):
        cpu_info = """ { "vendor": "Intel", "model": "core2duo",
        "arch": "i686","features": ["lahf_lm", "rdtscp"], "topology":
        {"cores": 1, "threads":1, "sockets": 1}} """

        cpu_info = six.text_type(cpu_info)

        self._do_test_compute_filter_extra_specs(
            ecaps={'cpu_info': cpu_info},
            especs={'capabilities:cpu_info:vendor': 'Intel'},
            passes=True)

    def test_compute_filter_fail_cpu_info_as_text_type_not_valid(self):
        cpu_info = "cpu_info"

        cpu_info = six.text_type(cpu_info)

        self._do_test_compute_filter_extra_specs(
            ecaps={'cpu_info': cpu_info},
            especs={'capabilities:cpu_info:vendor': 'Intel'},
            passes=False)

    def test_compute_filter_passes_extra_specs_simple(self):
        self._do_test_compute_filter_extra_specs(
            ecaps={'stats': {'opt1': 1, 'opt2': 2}},
            especs={'opt1': '1', 'opt2': '2', 'trust:trusted_host': 'true'},
            passes=True)

    def test_compute_filter_fails_extra_specs_simple(self):
        self._do_test_compute_filter_extra_specs(
            ecaps={'stats': {'opt1': 1, 'opt2': 2}},
            especs={'opt1': '1', 'opt2': '222', 'trust:trusted_host': 'true'},
            passes=False)

    def test_compute_filter_pass_extra_specs_simple_with_scope(self):
        self._do_test_compute_filter_extra_specs(
            ecaps={'stats': {'opt1': 1, 'opt2': 2}},
            especs={'capabilities:opt1': '1',
                    'trust:trusted_host': 'true'},
            passes=True)

    def test_compute_filter_pass_extra_specs_same_as_scope(self):
        # Make sure this still works even if the key is the same as the scope
        self._do_test_compute_filter_extra_specs(
            ecaps={'capabilities': 1},
            especs={'capabilities': '1'},
            passes=True)

    def test_compute_filter_extra_specs_simple_with_wrong_scope(self):
        self._do_test_compute_filter_extra_specs(
            ecaps={'opt1': 1, 'opt2': 2},
            especs={'wrong_scope:opt1': '1',
                    'trust:trusted_host': 'true'},
            passes=True)

    def test_compute_filter_extra_specs_pass_multi_level_with_scope(self):
        self._do_test_compute_filter_extra_specs(
            ecaps={'stats': {'opt1': {'a': 1, 'b': {'aa': 2}}, 'opt2': 2}},
            especs={'opt1:a': '1', 'capabilities:opt1:b:aa': '2',
                    'trust:trusted_host': 'true'},
            passes=True)
