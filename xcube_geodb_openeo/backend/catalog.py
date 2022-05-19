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
from typing import Optional, Tuple, Union

from ..core.vectorcube import VectorCube, Feature
from ..server.context import RequestContext

STAC_DEFAULT_COLLECTIONS_LIMIT = 10
STAC_DEFAULT_ITEMS_LIMIT = 10
STAC_MAX_ITEMS_LIMIT = 10000


def get_collections(ctx: RequestContext, url: str, limit: int, offset: int):
    links = get_collections_links(limit, offset, url, len(ctx.collection_ids))
    collections = {
        'collections': [
            _get_vector_cube_collection(
                ctx, _get_vector_cube(ctx, collection_id, with_items=False,
                                      bbox=None, limit=limit, offset=offset),
                details=False)
            for collection_id in ctx.collection_ids[offset:offset + limit]
        ],
        'links': links
    }
    return collections


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


def get_collection(ctx: RequestContext,
                   collection_id: str):
    vector_cube = _get_vector_cube(ctx, collection_id, with_items=False)
    return _get_vector_cube_collection(ctx, vector_cube, details=True)


def get_collection_items(ctx: RequestContext,
                         collection_id: str,
                         limit: int,
                         offset: int,
                         bbox: Optional[Tuple[float, float, float, float]] =
                         None):
    _validate(limit)
    vector_cube = _get_vector_cube(ctx, collection_id, with_items=True,
                                   limit=limit, offset=offset, bbox=bbox)
    stac_features = [
        _get_vector_cube_item(ctx,
                              vector_cube,
                              feature,
                              details=False)
        for feature in vector_cube.get("features", [])
    ]

    return {
        "type": "FeatureCollection",
        "features": stac_features,
        "timeStamp": _utc_now(),
        "numberMatched": vector_cube['total_feature_count'],
        "numberReturned": len(stac_features),
    }


def get_collection_item(ctx: RequestContext,
                        collection_id: str,
                        feature_id: str):
    vector_cube = _get_vector_cube(ctx, collection_id, True)
    for feature in vector_cube.get("features", []):
        if str(feature.get("id")) == feature_id:
            return _get_vector_cube_item(ctx,
                                         vector_cube,
                                         feature,
                                         details=True)
    raise ItemNotFoundException(
        f'feature {feature_id!r} not found in collection {collection_id!r}'
    )


def search(ctx: RequestContext):
    # TODO: implement me
    return {}


def _get_vector_cube_collection(ctx: RequestContext,
                                vector_cube: VectorCube,
                                details: bool = False):
    config = ctx.config
    vector_cube_id = vector_cube["id"]
    metadata = vector_cube.get("metadata", {})
    return {
        "stac_version": config['STAC_VERSION'],
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
                "href": ctx.get_url(
                    f"collections/{vector_cube_id}")
            },
            {
                "rel": "root",
                "href": ctx.get_url("collections")
            },
            # {
            #     "rel": "license",
            #     "href": ctx.get_url("TODO"),
            #     "title": "TODO"
            # }
        ]
    }


def _get_vector_cube_item(ctx: RequestContext,
                          vector_cube: VectorCube,
                          feature: Feature,
                          details: bool = False):
    config = ctx.config
    collection_id = vector_cube["id"]
    feature_id = feature["id"]
    feature_bbox = feature.get("bbox")
    feature_geometry = feature.get("geometry")
    feature_properties = feature.get("properties", {})

    return {
        "stac_version": config['STAC_VERSION'],
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
                'href': ctx.get_url(f'collections/{collection_id}/'
                                    f'items/{feature_id}')
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


def _get_vector_cube(ctx, collection_id: str, with_items: bool,
                     bbox: Union[Tuple[float, float, float, float], None] =
                     None,
                     limit: Optional[int] = None, offset: Optional[int] = 0):
    if collection_id not in ctx.collection_ids:
        raise CollectionNotFoundException(
            f'Unknown collection {collection_id!r}'
        )
    return ctx.get_vector_cube(collection_id, with_items, bbox, limit, offset)


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
