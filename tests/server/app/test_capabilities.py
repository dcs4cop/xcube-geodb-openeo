import json
import pkgutil
from typing import Dict

import yaml
from xcube.util import extension
from xcube.constants import EXTENSION_POINT_SERVER_APIS
from xcube.util.extension import ExtensionRegistry

from tests.server.app.base_test import BaseTest


class CapabilitiesTest(BaseTest):

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
        self.assertEqual('0.0.1.dev0', metainfo['backend_version'])
        self.assertEqual('0.9.0', metainfo['stac_version'])
        self.assertEqual('catalog', metainfo['type'])
        self.assertEqual('xcube-geodb-openeo', metainfo['id'])
        self.assertEqual(
            'xcube geoDB Server, openEO API', metainfo['title']
        )
        self.assertEqual(
            'Catalog of geoDB collections.', metainfo['description'])
        self.assertEqual(
            '/collections', metainfo['endpoints'][0]['path'])
        self.assertEqual(
            'GET', metainfo['endpoints'][0]['methods'][0])
        self.assertIsNotNone(metainfo['links'])

    def test_well_known_info(self):
        response = self.http.request(
            'GET', f'http://localhost:{self.port}/.well-known/openeo'
        )
        self.assertEqual(200, response.status)
        well_known_data = json.loads(response.data)
        self.assertEqual('http://www.brockmann-consult.de/xcube-geoDB-openEO',
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
