
# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# Copyright 2011 Red Hat, Inc.
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


from oslo_config import cfg

from jacket.storage import test


CONF = cfg.CONF
CONF.register_opt(cfg.StrOpt('conf_unittest',
                             default='foo',
                             help='for testing purposes only'))


class ConfigTestCase(test.TestCase):

    def setUp(self):
        super(ConfigTestCase, self).setUp()

    def test_declare(self):
        self.assertNotIn('answer', CONF)
        CONF.import_opt('answer', 'storage.tests.unit.declare_conf')
        self.assertIn('answer', CONF)
        self.assertEqual(42, CONF.answer)

        # Make sure we don't overwrite anything
        CONF.set_override('answer', 256)
        self.assertEqual(256, CONF.answer)
        CONF.import_opt('answer', 'storage.tests.unit.declare_conf')
        self.assertEqual(256, CONF.answer)

    def test_runtime_and_unknown_conf(self):
        self.assertNotIn('runtime_answer', CONF)
        import jacket.tests.storage.unit.runtime_conf
        self.assertIn('runtime_answer', CONF)
        self.assertEqual(54, CONF.runtime_answer)

    def test_long_vs_short_conf(self):
        CONF.clear()
        CONF.register_cli_opt(cfg.StrOpt('duplicate_answer_long',
                                         default='val',
                                         help='desc'))
        CONF.register_cli_opt(cfg.IntOpt('duplicate_answer',
                                         default=50,
                                         help='desc'))

        argv = ['--duplicate_answer=60']
        CONF(argv, default_config_files=[])
        self.assertEqual(60, CONF.duplicate_answer)
        self.assertEqual('val', CONF.duplicate_answer_long)

    def test_conf_leak_left(self):
        self.assertEqual('foo', CONF.conf_unittest)
        self.flags(conf_unittest='bar')
        self.assertEqual('bar', CONF.conf_unittest)

    def test_conf_leak_right(self):
        self.assertEqual('foo', CONF.conf_unittest)
        self.flags(conf_unittest='bar')
        self.assertEqual('bar', CONF.conf_unittest)

    def test_conf_overrides(self):
        self.assertEqual('foo', CONF.conf_unittest)
        self.flags(conf_unittest='bar')
        self.assertEqual('bar', CONF.conf_unittest)
        CONF.reset()
        self.assertEqual('foo', CONF.conf_unittest)
