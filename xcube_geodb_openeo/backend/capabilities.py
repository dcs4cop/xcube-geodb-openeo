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
from typing import Any
from typing import Mapping

from ..defaults import API_VERSION
from ..defaults import STAC_VERSION
from ..version import __version__

'''
Implements the endpoints listed under
https://openeo.org/documentation/1.0/developers/api/reference.html#tag/Capabilities 
'''


def get_root(config: Mapping[str, Any], base_url: str):
    return {
        'api_version': API_VERSION,
        'backend_version': __version__,
        'stac_version': STAC_VERSION,
        'type': 'Catalog',
        "id": config['geodb_openeo']['SERVER_ID'],
        "title": config['geodb_openeo']['SERVER_TITLE'],
        "description": config['geodb_openeo']['SERVER_DESCRIPTION'],
        "conformsTo": [
            f'https://api.stacspec.org/v1.0.0/{part}'
            for part in ['core', 'collections', 'ogcapi-features']
        ],
        'endpoints': [
            {'path': '/.well-known/openeo', 'methods': ['GET']},
            {'path': '/file_formats', 'methods': ['GET']},
            {'path': '/result', 'methods': ['POST']},
            {'path': '/collections', 'methods': ['GET']},
            {'path': '/processes', 'methods': ['GET']},
            {'path': '/collections/{collection_id}', 'methods': ['GET']},
            {'path': '/collections/{collection_id}/items', 'methods': ['GET']},
            {'path': '/collections/{collection_id}/items/{feature_id}',
             'methods': ['GET']},
        ],
        "links": [
            {
                "rel": "root",
                "href": f"{base_url}/",
                "type": "application/json",
                "title": "this document"
            },
            {
                "rel": "self",
                "href": f"{base_url}/",
                "type": "application/json",
                "title": "this document"
            },
            {
                "rel": "service-desc",
                "href": f'{base_url}/openapi.json',
                "type": "application/vnd.oai.openapi+json;version=3.0",
                "title": "the API definition"
            },
            {
                "rel": "service-doc",
                "href": f"{base_url}/api.html",
                "type": "text/html",
                "title": "the API documentation"
            },
            {
                "rel": "conformance",
                "href": f"{base_url}/conformance",
                "type": "application/json",
                "title": "OGC API conformance classes"
                         " implemented by this server"
            },
            {
                "rel": "data",
                "href": f"{base_url}/collections",
                "type": "application/json",
                "title": "Information about the feature collections"
            }
        ]
    }


def get_well_known(config: Mapping[str, Any]):
    return {
        'versions': [
            {
                'url': config['geodb_openeo']['SERVER_URL'],
                'api_version': API_VERSION
            }
        ]
    }


# noinspection PyUnusedLocal
def get_conformance():
    return {
        "conformsTo": []
    }
