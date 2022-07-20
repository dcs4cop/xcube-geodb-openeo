import json
import pkgutil
from typing import Dict

import yaml
from xcube.constants import EXTENSION_POINT_SERVER_APIS
from xcube.util import extension
from xcube.util.extension import ExtensionRegistry

from . import test_utils
from .base_test import BaseTest


class DataDiscoveryTest(BaseTest):

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

    def test_collection(self):
        url = f'http://localhost:{self.port}/collections/collection_1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        collection_data = json.loads(response.data)
        self.assertIsNotNone(collection_data)

    def test_get_items(self):
        url = f'http://localhost:{self.port}/collections/collection_1/items'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertIsNotNone(items_data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(2, len(items_data['features']))

        test_utils.assert_hamburg(self, items_data['features'][0])
        test_utils.assert_paderborn(self, items_data['features'][1])

    def test_get_items_no_results(self):
        url = f'http://localhost:{self.port}/collections/empty_collection/items'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertIsNotNone(items_data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(0, len(items_data['features']))

    def test_get_item(self):
        url = f'http://localhost:{self.port}/collections/collection_1/items/1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        item_data = json.loads(response.data)
        test_utils.assert_paderborn(self, item_data)

    def test_get_items_filtered(self):
        url = f'http://localhost:{self.port}/collections/collection_1/items' \
              f'?limit=1&offset=1'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertIsNotNone(items_data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(1, len(items_data['features']))
        test_utils.assert_paderborn(self, items_data['features'][0])

    def test_get_items_invalid_filter(self):
        for invalid_limit in [-1, 0, 10001]:
            url = f'http://localhost:{self.port}/' \
                  f'collections/collection_1/items' \
                  f'?limit={invalid_limit}'
            response = self.http.request('GET', url)
            self.assertEqual(500, response.status)

    def test_get_items_by_bbox(self):
        bbox_param = '?bbox=9.01,50.01,10.01,51.01'
        url = f'http://localhost:{self.port}' \
              f'/collections/collection_1/items' \
              f'{bbox_param}'
        response = self.http.request('GET', url)
        self.assertEqual(200, response.status)
        items_data = json.loads(response.data)
        self.assertEqual('FeatureCollection', items_data['type'])
        self.assertIsNotNone(items_data['features'])
        self.assertEqual(1, len(items_data['features']))
