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
from typing import Optional, TypeVar
from typing import OrderedDict, Hashable

from xcube_geodb.core.geodb import GeoDBClient


def create_geodb_client(api_config: dict) -> GeoDBClient:
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


T = TypeVar('T')


class Cache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._cache: OrderedDict[Hashable, T] = OrderedDict()

    def get(self, key: Hashable) -> Optional[T]:
        if key not in self._cache:
            return None
        self._cache.move_to_end(key)
        return self._cache[key]

    def insert(self, key: Hashable, item: T) -> None:
        if len(self._cache) == self.capacity:
            self._cache.popitem(last=False)
        self._cache[key] = item
        self._cache.move_to_end(key)

    def clear(self) -> None:
        self._cache.clear()

    def get_keys(self):
        return list(self._cache.keys())

    def __len__(self) -> int:
        return len(self._cache)
