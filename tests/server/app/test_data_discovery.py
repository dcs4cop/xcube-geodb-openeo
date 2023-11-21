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
from xcube.constants import EXTENSION_POINT_SERVER_APIS
from xcube.server.testing import ServerTestCase
from xcube.util import extension
from xcube.util.extension import ExtensionRegistry

from xcube_geodb_openeo.defaults import STAC_EXTENSIONS
from . import test_utils


class DataDiscoveryTest(ServerTestCase):

    def add_extension(self, er: ExtensionRegistry) -> None:
        er.add_extension(
            loader=extension.import_component('xcube_geodb_openeo.api:api'),
            point=EXTENSION_POINT_SERVER_APIS,
            name='geodb-openeo')

    def add_config(self, config: Dict):
        data = pkgutil.get_data('tests', 'test_config.yml')
        config.update(yaml.safe_load(data))

    def test_collections(self):
        url = f'http://localhost:{self.port}/collections'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        collections_data = json.loads(response.data)
        self.assertIsNotNone(collections_data['collections'])
        self.assertIsNotNone(collections_data['links'])

        first_collection = collections_data['collections'][0]
        self.assertEqual("1.0.0", first_collection['stac_version'])
        self.assertEqual(
            ['https://stac-extensions.github.io/datacube/v2.2.0/schema.json',
             'https://stac-extensions.github.io/version/v1.0.0/schema.json'],
            first_collection['stac_extensions'])
        self.assertEqual(first_collection['type'], 'Collection')
        self.assertEqual('~collection_1', first_collection['id'])
        self.assertIsNotNone(first_collection['description'])
        self.assertIsNotNone(first_collection['license'])
        self.assertIsNotNone(first_collection['extent'])
        self.assertIsNotNone(first_collection['links'])
        self.assertEqual(4, len(first_collection['links']))

    def test_collection(self):
        url = f'http://localhost:{self.port}/collections/~collection_1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        collection_data = json.loads(response.data)
        self.assertEqual("1.0.0", collection_data['stac_version'])
        self.assertListEqual(STAC_EXTENSIONS,
                             collection_data['stac_extensions'])
        response_type = collection_data['type']
        self.assertEqual(response_type, "Collection")
        self.assertIsNotNone(collection_data['id'])
        self.assertIsNotNone(collection_data['description'])
        self.assertIsNotNone(collection_data['license'])
        self.assertEqual(2, len(collection_data['extent']))
        expected_spatial_extent = \
            {'bbox': [9.0, 52.0, 11.0, 54.0]}
        expected_temporal_extent = {'interval': [[None, None]]}
        self.assertEqual(expected_spatial_extent,
                         collection_data['extent']['spatial'])
        self.assertEqual(expected_temporal_extent,
                         collection_data['extent']['temporal'])
        self.assertEqual({'vector': {'axes': ['x', 'y'],
                                     'bbox': '(9.0, 52.0, 11.0, 54.0)',
                                     'geometry_types': ['Polygon'],
                                     'reference_system': '3246',
                                     'type': 'geometry'}},
                         collection_data['cube:dimensions'])
        self.assertIsNotNone(collection_data['summaries'])

    def test_get_items(self):
        url = f'http://localhost:{self.port}/collections/~collection_1/items'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertIsNotNone(items_data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(2, len(items_data['features']))

        test_utils.assert_hamburg(self, items_data['features'][0])
        test_utils.assert_paderborn(self, items_data['features'][1])

    def test_get_item(self):
        url = f'http://localhost:{self.port}/collections/~collection_1/items/1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        item_data = json.loads(response.data)
        test_utils.assert_hamburg(self, item_data)

    def test_get_items_filtered(self):
        url = f'http://localhost:{self.port}/collections/~collection_1/items' \
              f'?limit=1&offset=1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertIsNotNone(items_data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(1, len(items_data['features']))
        test_utils.assert_paderborn(self, items_data['features'][0])

    def test_get_items_by_bbox(self):
        bbox_param = '?bbox=9.01,50.01,10.01,51.01'
        url = f'http://localhost:{self.port}' \
              f'/collections/~collection_1/items' \
              f'{bbox_param}'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(2, len(items_data['features']))

    def test_not_existing_collection(self):
        url = f'http://localhost:{self.port}' \
              f'/collections/~non-existent-collection'
        response = self.http.request('GET', url)
        self.assertEqual(404, response.status)
