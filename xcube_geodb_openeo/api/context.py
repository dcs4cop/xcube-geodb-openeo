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
import datetime
import importlib
import re
from functools import cached_property
from typing import Any, List
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Tuple

from xcube.constants import LOG
from xcube.server.api import ApiContext
from xcube.server.api import Context

from ..core.tools import Cache
from ..core.vectorcube import Feature
from ..core.vectorcube import VectorCube
from ..core.vectorcube_provider import VectorCubeProvider
from ..defaults import default_config, STAC_VERSION, STAC_EXTENSIONS, \
    DEFAULT_VC_CACHE_SIZE


class GeoDbContext(ApiContext):

    @property
    def collection_ids(self) -> List[Tuple[str, str]]:
        return self.cube_provider.get_collection_keys()

    @property
    def config(self) -> Mapping[str, Any]:
        assert self._config is not None
        return self._config

    @config.setter
    def config(self, config: Mapping[str, Any]):
        assert isinstance(config, Mapping)
        self._config = dict(config)

    @cached_property
    def cube_provider(self) -> VectorCubeProvider:
        if not self.config:
            raise RuntimeError('config not set')
        cube_provider_class = \
            self.config['geodb_openeo']['vectorcube_provider_class']
        cube_provider_module = \
            cube_provider_class[:cube_provider_class.rindex('.')]
        class_name = cube_provider_class[cube_provider_class.rindex('.') + 1:]
        module = importlib.import_module(cube_provider_module)
        cls = getattr(module, class_name)
        return cls(self.config)

    @property
    def request(self) -> Mapping[str, Any]:
        assert self._request is not None
        return self._request

    def __init__(self, root: Context):
        super().__init__(root)
        self._cube_provider = None
        self._request = None
        # necessary because root.config and its sub-configs are not writable
        # so copy their config in a new dict
        self.config = dict(root.config)
        for key in default_config.keys():
            if key not in self.config['geodb_openeo']:
                unfrozen_dict = dict(self.config['geodb_openeo'])
                self.config['geodb_openeo'] = unfrozen_dict
                unfrozen_dict[key] = default_config[key]
        self._collections = {}
        self._vector_cube_cache = Cache(DEFAULT_VC_CACHE_SIZE)

    def update(self, prev_ctx: Optional["Context"]):
        pass

    def get_vector_cube(self, collection_id: Tuple[str, str],
                        bbox: Optional[Tuple[float, float, float, float]]) \
            -> VectorCube:
        vector_cube = self._vector_cube_cache.get((collection_id, bbox))
        if vector_cube:
            return vector_cube
        vector_cube = self.cube_provider.get_vector_cube(collection_id, bbox)
        self._vector_cube_cache.insert((collection_id, bbox), vector_cube)
        return vector_cube

    @property
    def collections(self) -> Dict:
        assert self._collections is not None
        return self._collections

    @collections.setter
    def collections(self, collections: Dict):
        assert isinstance(collections, Dict)
        self._collections = collections

    def get_collections(self, base_url: str, limit: int, offset: int):
        url = f'{base_url}/collections'
        collection_list = []
        index = offset
        actual_limit = limit
        while index < offset + actual_limit and \
                index < len(self.collection_ids):
            collection_id = self.collection_ids[index]
            collection = self.get_collection(base_url, collection_id,
                                             full=False)
            if collection:
                collection_list.append(collection)
                LOG.debug(f'Loaded collection {collection_id} from geoDB')
            else:
                LOG.warning(f'Skipped empty collection {collection_id}')
                actual_limit = actual_limit + 1
            index += 1

        links = get_collections_links(limit, offset, url,
                                      len(self.collection_ids))

        self.collections = {
            'collections': collection_list,
            'links': links
        }

    def get_collection(self, base_url: str,
                       collection_id: Tuple[str, str],
                       full: bool = False) -> Optional[Dict]:
        if collection_id not in self.collection_ids:
            return None
        vector_cube = self.get_vector_cube(collection_id, bbox=None)
        return _get_vector_cube_collection(base_url, vector_cube, full)

    def get_collection_items(
            self, base_url: str, collection_id: Tuple[str, str], limit: int,
            offset: int, bbox: Optional[Tuple[float, float, float, float]]
            = None) -> Dict:
        vector_cube = self.get_vector_cube(collection_id, bbox=bbox)
        stac_features = []
        for feature in vector_cube.load_features(limit, offset):
            _fix_time(feature)
            stac_features.append(
                _get_vector_cube_item(base_url, vector_cube, feature)
            )

        result = {'type': 'FeatureCollection', 'features': stac_features,
                  'timeStamp': _utc_now(),
                  'numberMatched': vector_cube.feature_count,
                  'numberReturned': len(stac_features),
                  'links': [
                      {
                          'rel': 'self',
                          'href': f'{base_url}/collections/'
                                  f'{vector_cube.id}/items',
                          'type': 'application/json'
                      },
                      {
                          'rel': 'root',
                          'href': f'{base_url}',
                          'type': 'application/json'
                      },
                      {
                          'rel': 'items',
                          'href': f'{base_url}/collections/'
                                  f'{vector_cube.id}/items',
                          'type': 'application/json'
                      }]
                  }

        if offset + limit < vector_cube.feature_count:
            new_offset = offset + limit
            result['links'].append(
                {
                    'rel': 'next',
                    'href': f'{base_url}/collections/{vector_cube.id}'
                            f'/items?limit={limit}&offset={new_offset}'
                })

        return result

    def get_collection_item(self, base_url: str,
                            collection_id: Tuple[str, str],
                            feature_id: str):
        vector_cube = self.get_vector_cube(collection_id, bbox=None)
        feature = vector_cube.get_feature(feature_id)
        if feature:
            return _get_vector_cube_item(base_url, vector_cube, feature)
        raise ItemNotFoundException(
            f'feature {feature_id!r} not found in collection {collection_id!r}'
        )

    def transform_bbox(self, collection_id: Tuple[str, str],
                       bbox: Tuple[float, float, float, float],
                       crs: int) -> Tuple[float, float, float, float]:
        from xcube_geodb.core.geodb import GeoDBClient
        vector_cube = self.get_vector_cube(collection_id, bbox=None)
        return GeoDBClient.transform_bbox_crs(bbox, vector_cube.srid, crs)

def get_collections_links(limit: int, offset: int, url: str,
                          collection_count: int):
    links = []
    root_url = url.replace('/collections', '')
    root_link = {'rel': 'root',
                 'href': f'{root_url}',
                 'title': 'root'}
    self_link = {'rel': 'self',
                 'href': f'{url}',
                 'title': 'self'}
    next_offset = offset + limit
    next_link = {'rel': 'next',
                 'href': f'{url}?limit={limit}&offset='f'{next_offset}',
                 'title': 'next'}
    prev_offset = offset - limit
    prev_link = {'rel': 'prev',
                 'href': f'{url}?limit={limit}&offset='f'{prev_offset}',
                 'title': 'prev'}
    first_link = {'rel': 'first',
                  'href': f'{url}?limit={limit}&offset=0',
                  'title': 'first'}
    last_offset = collection_count - limit
    last_link = {'rel': 'last',
                 'href': f'{url}?limit={limit}&offset='f'{last_offset}',
                 'title': 'last'}

    links.append(root_link)
    links.append(self_link)
    if next_offset < collection_count:
        links.append(next_link)
    if offset > 0:
        links.append(prev_link)
        links.append(first_link)
    if limit + offset < collection_count:
        links.append(last_link)

    return links


def _get_vector_cube_collection(base_url: str,
                                vector_cube: VectorCube,
                                full: bool = False) -> Optional[Dict]:
    vector_cube_id = vector_cube.id
    metadata = vector_cube.get_metadata(full)
    vector_cube_collection = {
        'stac_version': STAC_VERSION,
        'stac_extensions': STAC_EXTENSIONS,
        'type': 'Collection',
        'id': vector_cube_id,
        'title': metadata.get('title', ''),
        'description': metadata.get('description', 'No description '
                                                   'available.'),
        'license': metadata.get('license', 'proprietary'),
        'keywords': metadata.get('keywords', []),
        'providers': metadata.get('providers', []),
        'extent': metadata.get('extent', {}),
        'links': [
            {
                'rel': 'self',
                'href': f'{base_url}/collections/{vector_cube_id}',
                "type": "application/json"
            },
            {
                'rel': 'root',
                'href': f'{base_url}',
                "type": "application/json"
            },
            {
                'rel': 'parent',
                'href': f'{base_url}/collections/',
                "type": "application/json"
            },
            {
                'rel': 'items',
                'href': f'{base_url}/collections/{vector_cube_id}/items',
                "type": "application/json"
            }
        ]
    }
    if full:
        geometry_types = vector_cube.get_geometry_types()
        bbox = vector_cube.get_bbox()
        z_dim = vector_cube.get_vertical_dim()
        axes = ['x', 'y', 'z'] if z_dim else ['x', 'y']
        srid = vector_cube.srid
        vector_cube_collection['cube:dimensions'] = {
            'vector': {
                'type': 'geometry',
                'axes': axes,
                'bbox': str(bbox),
                'geometry_types': geometry_types,
                'reference_system': srid
            }
        }
        vector_cube_collection['summaries'] = (metadata['summaries']
                                               if 'summaries' in metadata
                                               else {})
    if 'version' in metadata:
        vector_cube_collection['version'] = metadata['version']
    return vector_cube_collection


def _get_vector_cube_item(base_url: str, vector_cube: VectorCube,
                          feature: Feature):
    collection_id = vector_cube.id
    feature_id = feature['id']
    feature_bbox = feature.get('bbox')
    feature_geometry = feature.get('geometry')
    feature_properties = feature.get('properties', {})

    item = {
        'stac_version': STAC_VERSION,
        'stac_extensions': ['https://schemas.stacspec.org/v1.0.0/item-spec/'
                            'json-schema/item.json'],
        'type': 'Feature',
        'id': feature_id,
        'bbox': feature_bbox,
        'geometry': feature_geometry,
        'properties': feature_properties,
        'collection': collection_id,
        'links': [
            {
                'rel': 'self',
                'href': f'{base_url}/collections/'
                        f'{collection_id}/items/{feature_id}'
            },
            {
                'rel': 'root',
                'href': f'{base_url}',
                'type': 'application/json'
            },
            {
                'rel': 'parent',
                'href': f'{base_url}/collections',
                'type': 'application/json'
            },
            {
                'rel': 'collection',
                'href': f'{base_url}/collections/{collection_id}',
                'type': 'application/json'
            }            
        ],
        'assets': {}
    }
    return item


def _utc_now():
    return datetime \
               .datetime \
               .utcnow() \
               .replace(microsecond=0) \
               .isoformat() + 'Z'


def _fix_time(feature):
    time_column = _get_col_name(feature, ['date', 'time', 'timestamp',
                                          'datetime'])
    props = feature['properties']
    if time_column and time_column != 'datetime':
        props['datetime'] = props[time_column]
        del props[time_column]
    if 'datetime' not in props:
        props['datetime'] = (datetime.datetime
                             .strptime('19700101', '%Y%M%d')
                             .isoformat() + 'Z')
    if re.match('^\d\d\d\d.\d\d.\d\d$', props['datetime']):
        props['datetime'] = props['datetime'] + 'T00:00:00Z'
    is_tz_aware = (props['datetime'].endswith('Z')
                   or props['datetime'].endswith('+00:00'))
    if props['datetime'] and not is_tz_aware:
        props['datetime'] = props['datetime'] + 'Z'


def _get_col_name(feature: Feature, possible_names: List[str]) \
        -> Optional[str]:
    for key in feature['properties'].keys():
        if key in possible_names:
            return key
    return None


class CollectionNotFoundException(Exception):
    pass


class ItemNotFoundException(Exception):
    pass


class InvalidParameterException(Exception):
    pass
