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
from functools import cached_property
from typing import Any
from typing import Dict
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple

from xcube.server.api import ApiContext
from xcube.server.api import Context

from ..core.datastore import DataStore
from ..core.vectorcube import VectorCube
from ..core.vectorcube import Feature
from ..defaults import default_config
from ..server.config import STAC_VERSION

STAC_DEFAULT_COLLECTIONS_LIMIT = 10
STAC_DEFAULT_ITEMS_LIMIT = 10
STAC_MAX_ITEMS_LIMIT = 10000


class GeoDbContext(ApiContext):

    @cached_property
    def collection_ids(self) -> Sequence[str]:
        return tuple(self.data_store.get_collection_keys())

    @property
    def config(self) -> Mapping[str, Any]:
        assert self._config is not None
        return self._config

    @config.setter
    def config(self, config: Mapping[str, Any]):
        assert isinstance(config, Mapping)
        self._config = dict(config)

    @cached_property
    def data_store(self) -> DataStore:
        if not self.config:
            raise RuntimeError('config not set')
        data_store_class = self.config['geodb_openeo']['datastore_class']
        data_store_module = data_store_class[:data_store_class.rindex('.')]
        class_name = data_store_class[data_store_class.rindex('.') + 1:]
        module = importlib.import_module(data_store_module)
        cls = getattr(module, class_name)
        return cls(self.config)

    @property
    def request(self) -> Mapping[str, Any]:
        assert self._request is not None
        return self._request

    def __init__(self, root: Context):
        super().__init__(root)
        self._request = None
        self.config = root.config
        for key in default_config.keys():
            if key not in self.config['geodb_openeo']:
                self.config['geodb_openeo'][key] = default_config[key]
        self._collections = {}

    def update(self, prev_ctx: Optional["Context"]):
        pass

    def get_vector_cube(self, collection_id: str, with_items: bool,
                        bbox: Optional[Tuple[float, float, float, float]],
                        limit: Optional[int], offset: Optional[int]) \
            -> VectorCube:
        return self.data_store.get_vector_cube(collection_id, with_items,
                                               bbox, limit, offset)


    @property
    def collections(self) -> Dict:
        assert self._collections is not None
        return self._collections

    @collections.setter
    def collections(self, collections: Dict):
        assert isinstance(collections, Dict)
        self._collections = collections

    def fetch_collections(self, base_url: str, limit: int, offset: int):
        url = f'{base_url}/collections'
        links = get_collections_links(limit, offset, url,
                                      len(self.collection_ids))
        collection_list = []
        for collection_id in self.collection_ids[offset:offset + limit]:
            vector_cube = self.get_vector_cube(collection_id, with_items=False,
                                               bbox=None, limit=limit,
                                               offset=offset)
            collection = _get_vector_cube_collection(base_url, vector_cube)
            collection_list.append(collection)

        self.collections = {
            'collections': collection_list,
            'links': links
        }

    def get_collection(self, base_url: str,
                       collection_id: str):
        vector_cube = self.get_vector_cube(collection_id, with_items=False,
                                           bbox=None, limit=None, offset=0)
        return _get_vector_cube_collection(base_url, vector_cube)

    def get_collection_items(self, base_url: str,
                             collection_id: str, limit: int, offset: int,
                             bbox: Optional[Tuple[float, float, float,
                                                  float]] = None):
        _validate(limit)
        vector_cube = self.get_vector_cube(collection_id, with_items=True,
                                           bbox=bbox, limit=limit,
                                           offset=offset)
        stac_features = [
            _get_vector_cube_item(base_url, vector_cube, feature)
            for feature in vector_cube.get("features", [])
        ]

        return {
            "type": "FeatureCollection",
            "features": stac_features,
            "timeStamp": _utc_now(),
            "numberMatched": vector_cube['total_feature_count'],
            "numberReturned": len(stac_features),
        }

    def get_collection_item(self, base_url: str,
                            collection_id: str,
                            feature_id: str):
        # nah. use different geodb-function, don't get full vector cube
        vector_cube = self.get_vector_cube(collection_id, with_items=True,
                                           bbox=None, limit=None, offset=0)
        for feature in vector_cube.get("features", []):
            if str(feature.get("id")) == feature_id:
                return _get_vector_cube_item(base_url, vector_cube, feature)
        raise ItemNotFoundException(
            f'feature {feature_id!r} not found in collection {collection_id!r}'
        )

    def transform_bbox(self, collection_id: str,
                       bbox: Tuple[float, float, float, float],
                       crs: int) -> Tuple[float, float, float, float]:
        return self.data_store.transform_bbox(collection_id, bbox, crs)


def get_collections_links(limit: int, offset: int, url: str,
                          collection_count: int):
    links = []
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

    if next_offset < collection_count:
        links.append(next_link)
    if offset > 0:
        links.append(prev_link)
        links.append(first_link)
    if limit + offset < collection_count:
        links.append(last_link)

    return links


def search():
    # TODO: implement me
    return {}


def _get_vector_cube_collection(base_url: str,
                                vector_cube: VectorCube):
    vector_cube_id = vector_cube["id"]
    metadata = vector_cube.get("metadata", {})
    return {
        "stac_version": STAC_VERSION,
        "stac_extensions": ["xcube-geodb"],
        "id": vector_cube_id,
        "title": metadata.get("title", ""),
        "description": metadata.get("description", "No description "
                                                   "available."),
        "license": metadata.get("license", "proprietary"),
        "keywords": metadata.get("keywords", []),
        "providers": metadata.get("providers", []),
        "extent": metadata.get("extent", {}),
        "summaries": metadata.get("summaries", {}),
        "links": [
            {
                "rel": "self",
                "href": f"{base_url}/collections/{vector_cube_id}"
            },
            {
                "rel": "root",
                "href": f"{base_url}/collections/"
            },
            # {
            #     "rel": "license",
            #     "href": ctx.get_url("TODO"),
            #     "title": "TODO"
            # }
        ]
    }


def _get_vector_cube_item(base_url: str, vector_cube: VectorCube,
                          feature: Feature):
    collection_id = vector_cube["id"]
    feature_id = feature["id"]
    feature_bbox = feature.get("bbox")
    feature_geometry = feature.get("geometry")
    feature_properties = feature.get("properties", {})

    return {
        "stac_version": STAC_VERSION,
        "stac_extensions": ["xcube-geodb"],
        "type": "Feature",
        "id": feature_id,
        "bbox": feature_bbox,
        "geometry": feature_geometry,
        "properties": feature_properties,
        "collection": collection_id,
        "links": [
            {
                "rel": "self",
                "href": f"{base_url}/collections/"
                        f"{collection_id}/items/{feature_id}"
            }
        ],
        "assets": {
            "analytic": {
                # TODO
            },
            "visual": {
                # TODO
            },
            "thumbnail": {
                # TODO
            }
        }
    }


def _utc_now():
    return datetime \
               .datetime \
               .utcnow() \
               .replace(microsecond=0) \
               .isoformat() + 'Z'


def _validate(limit: int):
    if limit < 1 or limit > STAC_MAX_ITEMS_LIMIT:
        raise InvalidParameterException(f'if specified, limit has to be '
                                        f'between 1 and '
                                        f'{STAC_MAX_ITEMS_LIMIT}')


class CollectionNotFoundException(Exception):
    pass


class ItemNotFoundException(Exception):
    pass


class InvalidParameterException(Exception):
    pass
