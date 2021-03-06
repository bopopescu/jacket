# Copyright 2011 Justin Santa Barbara
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

from lxml import etree

from jacket.api.storage.storage import common
from jacket.tests.storage.functional import functional_helpers


class XmlTests(functional_helpers._FunctionalTestBase):
    """Some basic XML sanity checks."""

    # FIXME(ja): does storage need limits?
    # def test_namespace_limits(self):
    #     headers = {}
    #     headers['Accept'] = 'application/xml'

    #     response = self.api.api_request('/limits', headers=headers)
    #     data = response.read()
    #     LOG.debug("data: %s" % data)
    #     root = etree.XML(data)
    #     self.assertEqual(root.nsmap.get(None), xmlutil.XMLNS_COMMON_V10)

    def test_namespace_volumes(self):
        headers = {}
        headers['Accept'] = 'application/xml'

        response = self.api.api_request('/volumes', headers=headers,
                                        stream=True)
        data = response.raw
        root = etree.parse(data).getroot()
        self.assertEqual(common.XML_NS_V2, root.nsmap.get(None))
