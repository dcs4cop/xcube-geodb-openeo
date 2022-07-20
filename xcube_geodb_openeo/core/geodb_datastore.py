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

import os

from functools import cached_property
from typing import Tuple
from typing import Optional
from typing import Mapping
from typing import Any

from .datastore import DataStore
from xcube_geodb.core.geodb import GeoDBClient

from .vectorcube import VectorCube


class GeoDBDataStore(DataStore):

    def __init__(self, config: Mapping[str, Any]):
        self.config = config

    @cached_property
    def geodb(self):
        assert self.config

        api_config = self.config['geodb_openeo']
        server_url = api_config['postgrest_url']
        server_port = api_config['postgrest_port']
        client_id = api_config['client_id'] \
            if 'client_id' in api_config \
            else os.getenv('XC_GEODB_OPENEO_CLIENT_ID')
        client_secret = api_config['client_secret'] \
            if 'client_secret' in api_config \
            else os.getenv('XC_GEODB_OPENEO_CLIENT_SECRET')
        auth_domain = api_config['auth_domain']

        return GeoDBClient(
            server_url=server_url,
            server_port=server_port,
            client_id=client_id,
            client_secret=client_secret,
            auth_aud=auth_domain
        )

    def get_collection_keys(self):
        database_names = self.geodb.get_my_databases().get('name').array
        collections = None
        for n in database_names:
            if collections:
                collections.concat(self.geodb.get_my_collections(n))
            else:
                collections = self.geodb.get_my_collections(n)
        return collections.get('collection')

    def get_vector_cube(self, collection_id: str, with_items: bool,
                        bbox: Tuple[float, float, float, float] = None,
                        limit: Optional[int] = None, offset: Optional[int] =
                        0) \
            -> VectorCube:
        vector_cube = self.geodb.get_collection_info(collection_id)
        vector_cube['id'] = collection_id
        vector_cube['features'] = []
        if bbox:
            vector_cube['total_feature_count'] = \
                int(self.geodb.count_collection_by_bbox(
                    collection_id, bbox)['ct'][0])
        else:
            vector_cube['total_feature_count'] = \
                int(self.geodb.count_collection_by_bbox(
                    collection_id, (-180, 90, 180, -90))['ct'][0])

        if with_items:
            if bbox:
                items = self.geodb.get_collection_by_bbox(collection_id, bbox,
                                                          limit=limit,
                                                          offset=offset)
            else:
                items = self.geodb.get_collection(collection_id, limit=limit,
                                                  offset=offset)
            self.add_items_to_vector_cube(items, vector_cube)

        collection_bbox = self.geodb.get_collection_bbox(collection_id)
        if collection_bbox:
            srid = self.geodb.get_collection_srid(collection_id)
            if srid is not None and srid != '4326':
                collection_bbox = self.geodb.transform_bbox_crs(
                    collection_bbox,
                    srid, '4326',
                )

        properties = self.geodb.get_properties(collection_id)
        summaries = {
            'properties': []
        }
        for p in properties['column_name'].to_list():
            summaries['properties'].append({'name': p})
        vector_cube['metadata'] = {
            'title': collection_id,
            'extent': {
                'spatial': {
                    'bbox': collection_bbox,
                    'crs': 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'
                },
                'temporal': {
                    'interval': [['null']]
                }
            },
            'summaries': summaries
        }
        return vector_cube

    def transform_bbox(self, collection_id: str,
                       bbox: Tuple[float, float, float, float],
                       crs: int) -> Tuple[float, float, float, float]:
        srid = self.geodb.get_collection_srid(collection_id)
        if srid == crs:
            return bbox
        return self.geodb.transform_bbox_crs(bbox, crs, srid)
