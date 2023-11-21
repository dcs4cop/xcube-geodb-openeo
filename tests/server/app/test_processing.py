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
import unittest
from typing import Dict

import yaml
from xcube.constants import EXTENSION_POINT_SERVER_APIS
from xcube.server.testing import ServerTestCase
from xcube.util import extension
from xcube.util.extension import ExtensionRegistry

from xcube_geodb_openeo.backend import processes
from xcube_geodb_openeo.backend.processes import LoadCollection
from . import test_utils


@unittest.skip
class ProcessingTest(ServerTestCase):

    def add_extension(self, er: ExtensionRegistry) -> None:
        er.add_extension(
            loader=extension.import_component('xcube_geodb_openeo.api:api'),
            point=EXTENSION_POINT_SERVER_APIS, name='geodb-openeo'
        )

    def add_config(self, config: Dict):
        data = pkgutil.get_data('tests', 'test_config.yml')
        config.update(yaml.safe_load(data))

    def test_get_predefined_processes(self):
        response = self.http.request('GET',
                                     f'http://localhost:{self.port}/processes')
        self.assertEqual(200, response.status)
        self.assertTrue(
            'application/json' in response.headers['content-type']
        )
        processes_resp = json.loads(response.data)
        self.assertTrue('processes' in processes_resp)
        self.assertTrue('links' in processes_resp)

        processes_md = processes_resp['processes']
        self.assertTrue(len(processes_md) > 0)
        load_collection = None
        for p in processes_md:
            self.assertTrue('id' in p)
            self.assertTrue('description' in p)
            self.assertTrue('parameters' in p)
            self.assertTrue('returns' in p)

            if p['id'] == 'load_collection':
                load_collection = p

        self.assertIsNotNone(load_collection)
        self.assertEqual(1, len(load_collection['categories']))
        self.assertTrue('import', load_collection['categories'][0])

        self.assertTrue('Load a collection.', load_collection['summary'])

        self.assertTrue('Loads a collection from the current back-end '
                        'by its id and returns it as a vector cube.'
                        'The data that is added to the data cube can be'
                        ' restricted with the parameters'
                        '"spatial_extent" and "properties".'
                        , load_collection['description'])

        self.assertEqual(list, type(load_collection['parameters']))

        collection_param = None
        database_param = None
        spatial_extent_param = None
        self.assertEqual(3, len(load_collection['parameters']))
        for p in load_collection['parameters']:
            self.assertEqual(dict, type(p))
            self.assertTrue('name' in p)
            self.assertTrue('description' in p)
            self.assertTrue('schema' in p)
            if p['name'] == 'id':
                collection_param = p
            if p['name'] == 'database':
                database_param = p
            if p['name'] == 'spatial_extent':
                spatial_extent_param = p

        self.assertIsNotNone(collection_param)
        self.assertIsNotNone(database_param)
        self.assertIsNotNone(spatial_extent_param)

        self.assertEqual('string', collection_param['schema']['type'])
        self.assertEqual(dict, type(collection_param['schema']))

        self.assertEqual(dict, type(database_param['schema']))
        self.assertEqual('string', database_param['schema']['type'])
        self.assertEqual(True, database_param['optional'])

        self.assertEqual(list, type(spatial_extent_param['schema']))

        self.assertIsNotNone(load_collection['returns'])
        self.assertEqual(dict, type(load_collection['returns']))
        self.assertTrue('schema' in load_collection['returns'])
        return_schema = load_collection['returns']['schema']
        self.assertEqual(dict, type(return_schema))
        self.assertEqual('object', return_schema['type'])
        self.assertEqual('vector-cube', return_schema['subtype'])

    def test_get_file_formats(self):
        response = self.http.request('GET', f'http://localhost:{self.port}'
                                            f'/file_formats')
        self.assertEqual(200, response.status)
        self.assertTrue(
            'application/json' in response.headers['content-type']
        )
        formats = json.loads(response.data)
        self.assertTrue('input' in formats)
        self.assertTrue('output' in formats)

    def test_result(self):
        body = json.dumps({"process": {
            "id": "load_collection",
            "parameters": {
                "id": "collection_1",
                "spatial_extent": None
            }
        }})
        response = self.http.request('POST',
                                     f'http://localhost:{self.port}/result',
                                     body=body,
                                     headers={
                                         'content-type': 'application/json'
                                     })

        self.assertEqual(200, response.status)
        vector_cube = json.loads(response.data)
        self.assertEqual(list, type(vector_cube))
        self.assertIsNotNone(vector_cube)
        self.assertEqual(2, len(vector_cube))

        test_utils.assert_hamburg_data(self, vector_cube[0])
        test_utils.assert_paderborn_data(self, vector_cube[1])

    def test_result_bbox(self):
        body = json.dumps({"process": {
            "id": "load_collection",
            "parameters": {
                "id": "collection_1",
                "spatial_extent": {
                    "bbox": "(33, -10, 71, 43)",
                    "crs": 4326
                }
            }
        }})
        response = self.http.request('POST',
                                     f'http://localhost:{self.port}/result',
                                     body=body,
                                     headers={
                                         'content-type': 'application/json'
                                     })

        self.assertEqual(200, response.status)
        vector_cube = json.loads(response.data)
        self.assertEqual(list, type(vector_cube))
        self.assertIsNotNone(vector_cube)
        self.assertEqual(1, len(vector_cube))

        test_utils.assert_hamburg_data(self, vector_cube[0])

    def test_result_bbox_default_crs(self):
        body = json.dumps({"process": {
            "id": "load_collection",
            "parameters": {
                "id": "collection_1",
                "spatial_extent": {
                    "bbox": "(33, -10, 71, 43)"
                }
            }
        }})
        response = self.http.request('POST',
                                     f'http://localhost:{self.port}/result',
                                     body=body,
                                     headers={
                                         'content-type': 'application/json'
                                     })

        self.assertEqual(200, response.status)
        vector_cube = json.loads(response.data)
        self.assertEqual(list, type(vector_cube))
        self.assertIsNotNone(vector_cube)
        self.assertEqual(1, len(vector_cube))
        test_utils.assert_hamburg_data(self, vector_cube[0])

    def test_result_missing_parameters(self):
        body = json.dumps({'process': {
            'id': 'load_collection',
            'parameters': {}
        }})
        response = self.http.request('POST',
                                     f'http://localhost:{self.port}/result',
                                     body=body,
                                     headers={
                                         'content-type': 'application/json'
                                     })
        self.assertEqual(400, response.status)
        message = json.loads(response.data)
        self.assertTrue('Request body must contain parameter \'id\'.' in
                        message['error']['message'])

    def test_result_no_query_param(self):
        response = self.http.request('POST',
                                     f'http://localhost:{self.port}/result')
        self.assertEqual(400, response.status)
        message = json.loads(response.data)
        self.assertTrue('Request body must contain key \'process\'.' in
                        message['error']['message'])

    def test_invalid_process_id(self):
        with self.assertRaises(ValueError):
            processes.get_processes_registry().get_process('miau!')

    def test_translate_parameters(self):
        lc = LoadCollection({
            "id": "load_collection",
            "summary": "Load a collection"
        })
        query_params = {
            'id': 'collection_1',
            'spatial_extent': None
        }
        backend_params = lc.translate_parameters(query_params)
        self.assertEqual(backend_params['collection_id'], 'collection_1')
        self.assertIsNone(backend_params['bbox'])
        self.assertIsNone(backend_params['crs'])

    def test_translate_parameters_with_bbox(self):
        lc = LoadCollection({
            "id": "load_collection",
            "summary": "Load a collection"
        })
        query_params = {
            'id': 'collection_1',
            'spatial_extent': {
                'bbox': (33, -10, 71, 43),
                'crs': 4326
            }
        }
        backend_params = lc.translate_parameters(query_params)
        self.assertEqual(backend_params['collection_id'], 'collection_1')
        self.assertEqual((33, -10, 71, 43), backend_params['bbox'])
        self.assertEqual(4326, backend_params['crs'])
