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

import unittest
import xcube_geodb_openeo.api.context as context


class ContextTest(unittest.TestCase):

    def test_get_collections_links(self):
        links = context.get_collections_links(
            2, 6, 'http://server.hh/collections', 10)
        self.assertEqual([
            {'href': 'http://server.hh', 'rel': 'root', 'title': 'root'},
            {'href': 'http://server.hh/collections',
             'rel': 'self', 'title': 'self'},
            {'href': 'http://server.hh/collections?limit=2&offset=8',
             'rel': 'next',
             'title': 'next'},
            {'href': 'http://server.hh/collections?limit=2&offset=4',
             'rel': 'prev',
             'title': 'prev'},
            {'href': 'http://server.hh/collections?limit=2&offset=0',
             'rel': 'first',
             'title': 'first'},
            {'href': 'http://server.hh/collections?limit=2&offset=8',
             'rel': 'last',
             'title': 'last'}], links)

        links = context.get_collections_links(
            3, 0, 'http://server.hh/collections', 5)
        self.assertEqual(
            [{'href': 'http://server.hh', 'rel': 'root', 'title': 'root'},
             {'href': 'http://server.hh/collections', 'rel': 'self',
              'title': 'self'},

             {'href': 'http://server.hh/collections?limit=3&offset=3',
              'rel': 'next',
              'title': 'next'},
             {'href': 'http://server.hh/collections?limit=3&offset=2',
             'rel': 'last',
             'title': 'last'}], links)

        links = context.get_collections_links(
            2, 8, 'http://server.hh/collections', 10)
        self.assertEqual([
            {'href': 'http://server.hh', 'rel': 'root', 'title': 'root'},
            {'href': 'http://server.hh/collections', 'rel': 'self',
             'title': 'self'},
            {'href': 'http://server.hh/collections?limit=2&offset=6',
             'rel': 'prev',
             'title': 'prev'},
            {'href': 'http://server.hh/collections?limit=2&offset=0',
             'rel': 'first',
             'title': 'first'}], links)

        links = context.get_collections_links(
            10, 0, 'http://server.hh/collections', 7)
        self.assertEqual(
            [{'href': 'http://server.hh', 'rel': 'root', 'title': 'root'},
             {'href': 'http://server.hh/collections', 'rel': 'self',
              'title': 'self'}], links)
