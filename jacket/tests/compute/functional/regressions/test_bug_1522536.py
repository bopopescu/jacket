# Copyright 2016 HPE, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo_config import cfg

import jacket.compute.scheduler.utils
import jacket.compute.servicegroup
from jacket.compute import test
from jacket.tests.compute import fixtures as nova_fixtures
from jacket.tests.compute.functional.api import client
from jacket.tests.compute.unit import cast_as_call
import jacket.tests.compute.unit.image.fake
from jacket.tests.compute.unit import policy_fixture

CONF = cfg.CONF


class TestServerGet(test.TestCase):
    REQUIRES_LOCKING = True

    def setUp(self):
        super(TestServerGet, self).setUp()
        self.useFixture(policy_fixture.RealPolicyFixture())
        api_fixture = self.useFixture(nova_fixtures.OSAPIFixture(
            api_version='v2.1'))

        self.api = api_fixture.api

        # the image fake backend needed for image discovery
        jacket.tests.compute.unit.image.fake.stub_out_image_service(self)

        self.start_service('conductor', manager=CONF.conductor.manager)
        self.flags(scheduler_driver='chance_scheduler')
        self.start_service('scheduler')
        self.network = self.start_service('network')
        self.compute = self.start_service('compute')

        self.useFixture(cast_as_call.CastAsCall(self.stubs))
        self.addCleanup(jacket.tests.compute.unit.image.fake.FakeImageService_reset)

        self.image_id = self.api.get_images()[0]['id']
        self.flavor_id = self.api.get_flavors()[0]['id']

    def test_id_overlap(self):
        """Regression test for bug #1522536.

        Before fixing this bug, getting a numeric id caused a 500
        error because it treated the numeric value as the db index,
        fetched the server, but then processing of extensions blew up.

        Since we have fixed this bug it returns a 404, which is
        expected. In future a 400 might be more appropriate.
        """
        server = dict(name='server1',
                      imageRef=self.image_id,
                      flavorRef=self.flavor_id)
        self.api.post_server({'server': server})
        self.assertRaises(client.OpenStackApiNotFoundException,
                          self.api.get_server, 1)
