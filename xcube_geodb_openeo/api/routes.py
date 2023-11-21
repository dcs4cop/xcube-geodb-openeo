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
import base64
import json
import sys
import requests

from openeo.internal.graph_building import PGNode
from xcube.constants import LOG
from xcube.server.api import ApiError
from xcube.server.api import ApiHandler
from xcube_geodb.core.geodb import GeoDBError

from .api import api
from .context import _fix_time
from ..backend import capabilities
from ..backend import processes
from ..defaults import STAC_DEFAULT_ITEMS_LIMIT, STAC_MAX_ITEMS_LIMIT, \
    STAC_MIN_ITEMS_LIMIT


def get_base_url(request):
    # noinspection PyProtectedMember
    base_url = f'{request._request.protocol}://' \
               f'{request._request.host}'
    return base_url


@api.route('/')
class RootHandler(ApiHandler):
    """
    Lists general information about the back-end, including which version and
    endpoints of the openEO API are supported. May also include billing
    information.
    """

    def get(self):
        """
        Information about the API version and supported endpoints / features.
        """
        base_url = get_base_url(self.request)
        self.response.finish(capabilities.get_root(self.ctx.config, base_url))


@api.route('/credentials/oidc')
class RootHandler(ApiHandler):
    """
    Initiates the authentication process.
    """

    def get(self):
        auth_endpoint = ('https://kc.brockmann-consult.de/auth/realms/'
                         'xcube-geodb-openeo/protocol/openid-connect/auth')
        # the values for client_id and redirect_uri must match the values
        # set in Keycloak
        payload = {'response_type': 'code',
                   'client_id': 'openeo-server',
                   'scope': 'openid',
                   'redirect_uri':
                       f'{get_base_url(self.request)}/create_access_token'}

        # construct a redirect
        self.response.set_status(302)

        # as the method cannot be changed using the xcube server framework, we
        # have to use GET as well, and thus construct a URL with the payload as
        # query params
        auth_endpoint = f'{auth_endpoint}?'
        for k in payload.keys():
            auth_endpoint = f'{auth_endpoint}{k}={payload[k]}&'
        auth_endpoint = auth_endpoint[:-1]
        self.response.set_header('Location', auth_endpoint)

        self.response.finish()


@api.route('/create_access_token')
class RootHandler(ApiHandler):
    """
    Creates and validates an access token.
    """

    def get(self):
        code = self.request.query['code'][0]
        clientId = self.ctx.config['geodb_openeo']['kc_clientId']
        secret = self.ctx.config['geodb_openeo']['kc_secret']
        credentials = (base64.b64encode(
            f'{clientId}:{secret}'.encode("ascii")).decode('ascii'))
        auth_token_url = ('https://kc.brockmann-consult.de/auth/realms/'
                          'xcube-geodb-openeo/protocol/openid-connect/token')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {credentials}'
        }

        payload = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f'{get_base_url(self.request)}/create_access_token'
        }
        resp = requests.post(auth_token_url, data=payload, headers=headers)
        print(f'got access token! See: {resp.text}')

@api.route('/.well-known/openeo')
class WellKnownHandler(ApiHandler):
    """
    Lists all implemented openEO versions supported by the service provider.
    This endpoint is the Well-Known URI (see RFC 5785) for openEO.
    """

    @api.operation(operationId='connect', summary='Well-Known URI')
    def get(self):
        """
        Returns the well-known information.
        """
        self.response.finish(capabilities.get_well_known(self.ctx.config))


@api.route('/processes')
class ProcessesHandler(ApiHandler):
    """
    Lists all predefined processes and returns detailed process descriptions,
    including parameters and return values.
    """

    @api.operation(operationId='processes', summary='Listing of processes')
    def get(self):
        """
        Returns the processes information.
        """
        registry = processes.get_processes_registry()
        self.response.finish({
            'processes': [p.metadata for p in registry.processes],
            'links': registry.get_links()}
        )


@api.route('/file_formats')
class FormatsHandler(ApiHandler):
    """
    Lists supported input and output file formats. Input file formats specify
    which file a back-end can read from.
    Output file formats specify which file a back-end can write to.
    """

    @api.operation(operationId='file_formats',
                   summary='Listing of supported file formats')
    def get(self):
        """
        Returns the supported file formats.
        """
        self.response.finish(processes.get_processes_registry()
                             .get_file_formats())


@api.route('/result')
class ResultHandler(ApiHandler):
    """
    Executes a user-defined process directly (synchronously) and the result
    will be downloaded.
    """

    @api.operation(operationId='result', summary='Execute process'
                                                 'synchronously.')
    def post(self):
        """
        Processes requested processing task and returns result.
        """
        if not self.request.body:
            raise (ApiError(
                400,
                'Request body must contain key \'process\'.'))

        processing_request = json.loads(self.request.body)['process']
        registry = processes.get_processes_registry()
        graph = processing_request['process_graph']
        pg_node = PGNode.from_flat_graph(graph)
        registry.get_process(pg_node.process_id)

        nodes = []
        current_node = pg_node
        while 'data' in current_node.arguments and 'from_node' in current_node.arguments['data']:
            nodes.append(current_node)
            current_node = current_node.arguments['data']['from_node']
        nodes.append(current_node)
        nodes.reverse()

        current_result = None
        for node in nodes:
            process = registry.get_process(node.process_id)
            expected_parameters = process.metadata['parameters']
            process_parameters = node.arguments
            process_parameters['input'] = current_result
            self.ensure_parameters(expected_parameters, process_parameters)
            process.parameters = process_parameters
            current_result = processes.submit_process_sync(process, self.ctx)

        current_result = json.dumps(current_result, default=str)
        self.response.finish(current_result)

    @staticmethod
    def ensure_parameters(expected_parameters, process_parameters):
        for ep in expected_parameters:
            is_optional_param = 'optional' in ep and ep['optional']
            if not is_optional_param:
                if ep['name'] not in process_parameters:
                    raise (ApiError(400,
                                    f'Request body must contain parameter'
                                    f' \'{ep["name"]}\'.'))


@api.route('/conformance')
class ConformanceHandler(ApiHandler):
    """
    Lists all conformance classes specified in OGC standards that the server
    conforms to.
    """

    def get(self):
        """
        Lists the conformance classes.
        """
        self.response.finish(capabilities.get_conformance())


@api.route('/collections')
@api.route('/collections/')
class CollectionsHandler(ApiHandler):
    """
    Lists available collections with at least the required information.
    """

    @api.operation(operationId='getCollections',
                   summary='Gets metadata of all available collections')
    def get(self):
        """
        Lists the available collections.

        Args:
            limit (int):  The optional limit parameter limits the number of
                          items that are presented in the response document.
            offset (int): Collections are listed starting at offset.
        """
        limit = _get_limit(self.request)
        offset = _get_offset(self.request)
        base_url = get_base_url(self.request)
        self.ctx.get_collections(base_url, limit, offset)
        self.response.finish(self.ctx.collections)


@api.route('/collections/{collection_id}')
@api.route('/collections/{collection_id}/')
class CollectionHandler(ApiHandler):
    """
    Lists all information about a specific collection specified by the
    identifier collection_id.
    """

    def get(self, collection_id: str):
        """
        Lists the collection information.
        """
        base_url = get_base_url(self.request)
        if '~' not in collection_id:
            self.response.set_status(404,
                                     f'Collection {collection_id} does '
                                     f'not exist')
            return
        db = collection_id.split('~')[0]
        name = collection_id.split('~')[1]
        collection = self.ctx.get_collection(base_url, (db, name), True)
        if collection:
            self.response.finish(collection)
        else:
            self.response.set_status(404,
                                     f'Collection {collection_id} does '
                                     f'not exist')


@api.route('/collections/{collection_id}/items')
@api.route('/collections/{collection_id}/items/')
class CollectionItemsHandler(ApiHandler):
    """
    Get features of the feature collection with id collectionId.
    """

    # noinspection PyIncorrectDocstring
    def get(self, collection_id: str):
        """
        Returns the features.

        Args:
            limit (int):  Optional, limits the number of items presented in
            the response document.
            offset (int): Optional, collections are listed starting at offset.
            bbox (array of numbers): Only features that intersect the bounding
                box are selected. Example: bbox=160.6,-55.95,-170,-25.89
        """
        limit = _get_limit(self.request, STAC_DEFAULT_ITEMS_LIMIT)
        limit = STAC_MAX_ITEMS_LIMIT if limit > STAC_MAX_ITEMS_LIMIT else limit
        limit = STAC_MIN_ITEMS_LIMIT if limit < STAC_MIN_ITEMS_LIMIT else limit
        offset = _get_offset(self.request)
        bbox = _get_bbox(self.request)
        base_url = get_base_url(self.request)
        db = collection_id.split('~')[0]
        name = collection_id.split('~')[1]
        items = self.ctx.get_collection_items(base_url, (db, name),
                                              limit, offset, bbox)
        self.response.finish(items, content_type='application/geo+json')


@api.route('/collections/{collection_id}/items/{item_id}')
class FeatureHandler(ApiHandler):
    """
    Fetch a single item.
    """

    def get(self, collection_id: str, item_id: str):
        """
        Returns the feature.
        """
        feature_id = item_id
        db = collection_id.split('~')[0]
        name = collection_id.split('~')[1]
        base_url = get_base_url(self.request)
        try:
            feature = self.ctx.get_collection_item(base_url, (db, name),
                                                   feature_id)
        except GeoDBError as e:
            if 'does not exist' in e.args[0]:
                LOG.warning(f'Not existing feature with id {feature_id} '
                            f'requested.')
            self.response.set_status(404,
                                     f'Feature {feature_id} does '
                                     f'not exist')
            return

        _fix_time(feature)
        self.response.finish(feature, content_type='application/geo+json')


@api.route('/api.html')
class FeatureHandler(ApiHandler):
    """
    Simply forwards to openapi.html
    """

    def get(self):
        self.response._handler.redirect('/openapi.html', status=301)


def _get_limit(request, default=sys.maxsize) -> int:
    limit = int(request.get_query_arg('limit')) if \
        request.get_query_arg('limit') \
        else default
    return limit


def _get_offset(request) -> int:
    return int(request.get_query_arg('offset')) if \
        request.get_query_arg('offset') \
        else 0


def _get_bbox(request):
    if request.get_query_arg('bbox'):
        bbox = str(request.get_query_arg('bbox'))
        return tuple(bbox.split(','))
    else:
        return None
