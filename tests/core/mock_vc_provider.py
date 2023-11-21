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

import importlib.resources as resources
import json
from datetime import datetime
from typing import Any, Dict, List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

import geojson
import shapely
import shapely.wkt as wkt
from geojson.geometry import Geometry

from xcube_geodb_openeo.core.geodb_datasource import DataSource, Feature
from xcube_geodb_openeo.core.vectorcube import VectorCube
from xcube_geodb_openeo.core.vectorcube_provider import VectorCubeProvider
from xcube_geodb_openeo.defaults import STAC_EXTENSIONS


class MockProvider(VectorCubeProvider, DataSource):

    # noinspection PyUnusedLocal
    def __init__(self, config: Mapping[str, Any]):
        with resources.open_text('tests', 'mock_collections.json') as text:
            mock_collections = json.load(text)['_MOCK_COLLECTIONS_LIST']
        self._MOCK_COLLECTIONS = {('', v["id"]): v for v in mock_collections}
        self.hh = 'POLYGON((9 52, 9 54, 11 54, 11 52, 10 53, 9.5 53.4, ' \
                  '9.2 52.1, 9 52))'
        self.pb = 'POLYGON((8.7 51.3, 8.7 51.8, 8.8 51.8, 8.8 51.3, 8.7 51.3))'

        self.bbox_hh = wkt.loads(self.hh).bounds
        self.bbox_pb = wkt.loads(self.pb).bounds

    def get_collection_keys(self) -> Sequence:
        return list(self._MOCK_COLLECTIONS.keys())

    def get_vector_cube(
            self, collection_id: Tuple[str, str],
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> VectorCube:
        return VectorCube(collection_id, self)

    def get_vector_dim(
            self,
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> List[Geometry]:

        hh = 'Polygon(((9, 52), (9, 54), (11, 54), (11, 52), (10, 53), ' \
             '(9.8, 53.4), (9.2, 52.1), (9, 52)))'
        pb = 'Polygon(((8.7, 51.3), (8.7, 51.8), (8.8, 51.8), (8.8, 51.3), ' \
             '(8.7, 51.3)))'

        return [geojson.dumps(shapely.geometry.mapping(wkt.loads(hh))),
                geojson.dumps(shapely.geometry.mapping(wkt.loads(pb)))]

    def get_srid(self) -> int:
        return 3246

    def get_feature_count(self) -> int:
        return 2

    def get_time_dim(
            self,
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> Optional[List[datetime]]:
        return None

    def get_time_dim_name(self) -> Optional[str]:
        return 'time'

    def get_vertical_dim(
            self,
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> Optional[List[Any]]:
        return None

    def load_features(self, limit: int = 2,
                      offset: int = 0, feature_id: Optional[str] = None,
                      with_stac_info: bool = False) -> \
            List[Feature]:

        hh_feature = {
            'stac_version': 15.1,
            'stac_extensions': ['https://schemas.stacspec.org/v1.0.0/'
                                'item-spec/json-schema/item.json'],
            'type': 'Feature',
            'id': '0',
            'bbox': [f'{self.bbox_hh[0]:.4f}',
                     f'{self.bbox_hh[1]:.4f}',
                     f'{self.bbox_hh[2]:.4f}',
                     f'{self.bbox_hh[3]:.4f}'],
            'properties': {'id': 1234,
                           'name': 'hamburg',
                           'geometry': 'mygeometry',
                           'population': 1000}
        }

        pb_feature = {
            'stac_version': 15.1,
            'stac_extensions': ['https://schemas.stacspec.org/v1.0.0/'
                                'item-spec/json-schema/item.json'],
            'type': 'Feature',
            'id': '1',
            'bbox': [f'{self.bbox_pb[0]:.4f}',
                     f'{self.bbox_pb[1]:.4f}',
                     f'{self.bbox_pb[2]:.4f}',
                     f'{self.bbox_pb[3]:.4f}'],
            'properties': {'id': 4321,
                           'name': 'paderborn',
                           'geometry': 'mygeometry',
                           'population': 100}
        }

        if limit == 1:
            return [pb_feature]

        return [hh_feature, pb_feature]

    def get_vector_cube_bbox(self) -> Tuple[float, float, float, float]:
        return wkt.loads(self.hh).bounds


    def get_geometry_types(self) -> List[str]:
        return ['Polygon']

    def get_metadata(self, full: bool = False) -> Dict:
        metadata = {
            'title': 'something',
            'extent': {
                'spatial': {
                    'bbox': [9.0, 52.0, 11.0, 54.0],
                },
                'temporal': {
                    'interval': [[None, None]]
                }
            },
            'summaries': {
                'column_names': 'col_names'
            },
        }
        return metadata

'''
    @staticmethod
    def add_items_to_vector_cube(
            collection: GeoDataFrame, vector_cube: VectorCube):
        bounds = collection.bounds
        for i, row in enumerate(collection.iterrows()):
            bbox = bounds.iloc[i]
            feature = row[1]
            coords = VectorCubeProvider._get_coords(feature)
            properties = {}
            for k, key in enumerate(feature.keys()):
                if not key == 'id' and not \
                        collection.dtypes.values[k].name == 'geometry':
                    if isinstance(feature[key], float) \
                            and math.isnan(float(feature[key])):
                        properties[key] = 'NaN'
                    else:
                        properties[key] = feature[key]

            vector_cube['features'].append({
                'stac_version': STAC_VERSION,
                'stac_extensions': STAC_EXTENSIONS,
                'type': 'Feature',
                'id': feature['id'],
                'bbox': [f'{bbox["minx"]:.4f}',
                         f'{bbox["miny"]:.4f}',
                         f'{bbox["maxx"]:.4f}',
                         f'{bbox["maxy"]:.4f}'],
                'geometry': coords,
                'properties': properties
            })
'''

'''
        data = {
            'id': ['0', '1'],
            'name': ['hamburg', 'paderborn'],
            'geometry': [Polygon(((9, 52), (9, 54), (11, 54), (11, 52),
                                  (10, 53), (9.8, 53.4), (9.2, 52.1),
                                  (9, 52))),
                         Polygon(((8.7, 51.3), (8.7, 51.8), (8.8, 51.8),
                                  (8.8, 51.3), (8.7, 51.3)))
                         ],
            'population': [1700000, 150000]
        }
        collection = geopandas.GeoDataFrame(data, crs="EPSG:4326")
        if bbox:
            # simply dropping one entry; we don't need to test this
            # logic here, as it is implemented within the geoDB module
            collection = collection.drop([1, 1])
        if limit:
            collection = collection[offset:offset + limit]
        vector_cube['id'] = collection_id
        vector_cube['features'] = []
        vector_cube['total_feature_count'] = len(collection)
        if with_items and collection_id != 'empty_collection':
            self.add_items_to_vector_cube(collection, vector_cube)
        GeoDBVectorSource.add_metadata(
            (8, 51, 12, 52), collection_id,
            DataFrame(columns=["collection", "column_name", "data_type"]),
            '0.3.1', vector_cube)

'''