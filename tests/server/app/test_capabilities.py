# The MIT License (MIT)
# Copyright (c) 2021/2022 by the xcube team and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import json
import pkgutil
from typing import Dict

import yaml
from xcube.server.testing import ServerTestCase
from xcube.util import extension
from xcube.constants import EXTENSION_POINT_SERVER_APIS
from xcube.util.extension import ExtensionRegistry


class CapabilitiesTest(ServerTestCase):

    def add_extension(self, er: ExtensionRegistry) -> None:
        er.add_extension(
            loader=extension.import_component('xcube_geodb_openeo.api:api'),
            point=EXTENSION_POINT_SERVER_APIS, name='geodb-openeo')

    def add_config(self, config: Dict):
        data = pkgutil.get_data('tests', 'test_config.yml')
        config.update(yaml.safe_load(data))

    def test_root(self):
        response = self.http.request('GET', f'http://localhost:{self.port}/')
        self.assertEqual(200, response.status)
        self.assertTrue(
            'application/json' in response.headers['content-type']
        )
        metainfo = json.loads(response.data)
        self.assertEqual('1.1.0', metainfo['api_version'])
        self.assertEqual('0.0.2.dev0', metainfo['backend_version'])
        self.assertEqual('1.0.0', metainfo['stac_version'])
        self.assertEqual('Catalog', metainfo['type'])
        self.assertEqual('xcube-geodb-openeo', metainfo['id'])
        self.assertEqual(
            'xcube geoDB Server, openEO API', metainfo['title']
        )
        self.assertEqual(
            'Catalog of geoDB collections.', metainfo['description'])
        self.assertEqual(
            '/.well-known/openeo', metainfo['endpoints'][0]['path'])
        self.assertEqual(
            'GET', metainfo['endpoints'][0]['methods'][0])

        self.assertEqual(
            '/result', metainfo['endpoints'][2]['path'])
        self.assertEqual(
            'POST', metainfo['endpoints'][2]['methods'][0])

        self.assertEqual(
            '/collections/{collection_id}/items', metainfo['endpoints'][6]['path'])
        self.assertEqual(
            'GET', metainfo['endpoints'][7]['methods'][0])
        self.assertIsNotNone(metainfo['links'])

    def test_well_known_info(self):
        response = self.http.request(
            'GET', f'http://localhost:{self.port}/.well-known/openeo'
        )
        self.assertEqual(200, response.status)
        well_known_data = json.loads(response.data)
        self.assertEqual('http://xcube-geoDB-openEO.de',
                         well_known_data['versions'][0]['url'])
        self.assertEqual('1.1.0',
                         well_known_data['versions'][0]['api_version'])

    def test_conformance(self):
        response = self.http.request(
            'GET', f'http://localhost:{self.port}/conformance'
        )
        self.assertEqual(200, response.status)
        conformance_data = json.loads(response.data)
        self.assertIsNotNone(conformance_data['conformsTo'])
