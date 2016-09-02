# Copyright 2011 University of Southern California
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
Unit Tests for instance types extra specs code
"""

from jacket.compute.cloud import arch
from jacket import context
from jacket.db import compute
from jacket.compute import exception
from jacket.compute import test


class InstanceTypeExtraSpecsTestCase(test.TestCase):

    def setUp(self):
        super(InstanceTypeExtraSpecsTestCase, self).setUp()
        self.context = context.get_admin_context()
        values = dict(name="cg1.4xlarge",
                      memory_mb=22000,
                      vcpus=8,
                      root_gb=1690,
                      ephemeral_gb=2000,
                      flavorid=105)
        self.specs = dict(cpu_arch=arch.X86_64,
                          cpu_model="Nehalem",
                          xpu_arch="fermi",
                          xpus="2",
                          xpu_model="Tesla 2050")
        values['extra_specs'] = self.specs
        ref = compute.flavor_create(self.context,
                               values)
        self.instance_type_id = ref["id"]
        self.flavorid = ref["flavorid"]

    def tearDown(self):
        # Remove the instance type from the database
        compute.flavor_destroy(self.context, "cg1.4xlarge")
        super(InstanceTypeExtraSpecsTestCase, self).tearDown()

    def test_instance_type_specs_get(self):
        actual_specs = compute.flavor_extra_specs_get(
                              self.context,
                              self.flavorid)
        self.assertEqual(self.specs, actual_specs)

    def test_flavor_extra_specs_delete(self):
        del self.specs["xpu_model"]
        compute.flavor_extra_specs_delete(self.context,
                                     self.flavorid,
                                     "xpu_model")
        actual_specs = compute.flavor_extra_specs_get(
                              self.context,
                              self.flavorid)
        self.assertEqual(self.specs, actual_specs)

    def test_instance_type_extra_specs_update(self):
        self.specs["cpu_model"] = "Sandy Bridge"
        compute.flavor_extra_specs_update_or_create(
                              self.context,
                              self.flavorid,
                              dict(cpu_model="Sandy Bridge"))
        actual_specs = compute.flavor_extra_specs_get(
                              self.context,
                              self.flavorid)
        self.assertEqual(self.specs, actual_specs)

    def test_instance_type_extra_specs_update_with_nonexisting_flavor(self):
        extra_specs = dict(cpu_arch=arch.X86_64)
        nonexisting_flavorid = "some_flavor_that_does_not_exist"
        self.assertRaises(exception.FlavorNotFound,
                          compute.flavor_extra_specs_update_or_create,
                          self.context, nonexisting_flavorid, extra_specs)

    def test_instance_type_extra_specs_create(self):
        net_attrs = {
            "net_arch": "ethernet",
            "net_mbps": "10000"
        }
        self.specs.update(net_attrs)
        compute.flavor_extra_specs_update_or_create(
                              self.context,
                              self.flavorid,
                              net_attrs)
        actual_specs = compute.flavor_extra_specs_get(
                              self.context,
                              self.flavorid)
        self.assertEqual(self.specs, actual_specs)

    def test_instance_type_get_with_extra_specs(self):
        instance_type = compute.flavor_get(
                            self.context,
                            self.instance_type_id)
        self.assertEqual(instance_type['extra_specs'],
                         self.specs)
        instance_type = compute.flavor_get(
                            self.context,
                            5)
        self.assertEqual(instance_type['extra_specs'], {})

    def test_instance_type_get_by_name_with_extra_specs(self):
        instance_type = compute.flavor_get_by_name(
                            self.context,
                            "cg1.4xlarge")
        self.assertEqual(instance_type['extra_specs'],
                         self.specs)
        instance_type = compute.flavor_get_by_name(
                            self.context,
                            "m1.small")
        self.assertEqual(instance_type['extra_specs'], {})

    def test_instance_type_get_by_flavor_id_with_extra_specs(self):
        instance_type = compute.flavor_get_by_flavor_id(
                            self.context,
                            105)
        self.assertEqual(instance_type['extra_specs'],
                         self.specs)
        instance_type = compute.flavor_get_by_flavor_id(
                            self.context,
                            2)
        self.assertEqual(instance_type['extra_specs'], {})

    def test_instance_type_get_all(self):
        types = compute.flavor_get_all(self.context)

        name2specs = {}
        for instance_type in types:
            name = instance_type['name']
            name2specs[name] = instance_type['extra_specs']

        self.assertEqual(name2specs['cg1.4xlarge'], self.specs)
        self.assertEqual(name2specs['m1.small'], {})
