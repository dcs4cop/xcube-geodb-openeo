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

import abc
from functools import cached_property
from typing import Tuple, Optional, List, Mapping, Any

from xcube_geodb.core.geodb import GeoDBClient

from .geodb_datasource import GeoDBVectorSource
from .tools import create_geodb_client
from .vectorcube import VectorCube


class VectorCubeProvider(abc.ABC):

    @abc.abstractmethod
    def get_collection_keys(self) -> List[Tuple[str, str]]:
        pass

    @abc.abstractmethod
    def get_vector_cube(
            self, collection_id: Tuple[str, str],
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> VectorCube:
        pass


class GeoDBProvider(VectorCubeProvider):

    def __init__(self, config: Mapping[str, Any]):
        self.config = config

    @cached_property
    def geodb(self) -> GeoDBClient:
        assert self.config
        api_config = self.config['geodb_openeo']
        return create_geodb_client(api_config)

    def get_collection_keys(self) -> List[Tuple[str, str]]:
        collections = self.geodb.get_my_collections()
        result = []
        collection_list = collections.get('collection')
        for idx, database in enumerate(collections.get('database')):
            collection_id = collection_list[idx]
            if collection_id:
                result.append((database, collection_id))

        return result

    def get_vector_cube(
            self, collection_id: Tuple[str, str],
            bbox: Optional[Tuple[float, float, float, float]] = None) \
            -> VectorCube:
        return VectorCube(collection_id,
                          GeoDBVectorSource(collection_id, self.geodb))
