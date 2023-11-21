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
import operator

import dateutil.parser
import importlib
import importlib.resources as resources
import json
import pytz

from abc import abstractmethod
from typing import Dict, List, Any, Callable

import shapely
from geojson import Feature, FeatureCollection
from xcube.server.api import ServerContextT
from openeo.internal.graph_building import PGNode
from ..core.vectorcube import StaticVectorCubeFactory, VectorCube


class Process:
    """
    This class represents a process. It contains the metadata, and the method
    "Execute".
    Instances can be passed as parameter to Processing.
    """

    def __init__(self, metadata: Dict):
        if not metadata:
            raise ValueError('Empty processor metadata provided.')
        self._metadata = metadata
        if 'module' in self._metadata:
            del self.metadata['module']
            del self.metadata['class_name']
        self._parameters = {}

    @property
    def metadata(self) -> Dict:
        return self._metadata

    @property
    def parameters(self) -> Dict:
        return self._parameters

    @parameters.setter
    def parameters(self, p: dict) -> None:
        self._parameters = p

    @abstractmethod
    def execute(self, parameters: dict, ctx: ServerContextT) -> Any:
        pass

    def translate_parameters(self, parameters: dict) -> dict:
        """
        Translate params from query params to backend params
        :param parameters: query params
        :return: backend params
        """
        return parameters


def read_default_processes() -> List[Process]:
    processes_specs = [j for j in
                       resources.contents(f'{__package__}.res.processes')
                       if j.lower().endswith('json')]
    processes = []
    for spec in processes_specs:
        with resources.open_binary(f'{__package__}.res.processes', spec) as f:
            metadata = json.loads(f.read())
            module = importlib.import_module(metadata['module'])
            class_name = metadata['class_name']
            cls = getattr(module, class_name)
            processes.append(cls(metadata))

    return processes


class ProcessRegistry:

    @property
    def processes(self) -> List[Process]:
        return self._processes

    def __init__(self):
        self._processes = []
        self.links = []
        self._add_default_processes()
        self._add_default_links()

    def add_process(self, process: Process) -> None:
        self.processes.append(process)

    def add_link(self, link: Dict) -> None:
        self.links.append(link)

    def get_links(self) -> List:
        return self.links.copy()

    def get_file_formats(self) -> Dict:
        return {
            "output": {
                "GTiff": {
                    "title": "GeoTiff",
                    "description": "Export to GeoTiff. Doesn't support cloud-optimized GeoTiffs (COGs) yet.",
                    "gis_data_types": [
                        "raster"
                    ],
                    "parameters": {
                        "tiled": {
                            "type": "boolean",
                            "description": "This option can be used to force creation of tiled TIFF files [true]. By default [false] stripped TIFF files are created.",
                            "default": "false"
                        },
                        "compress": {
                            "type": "string",
                            "description": "Set the compression to use.",
                            "default": "NONE",
                            "enum": [
                                "JPEG",
                                "LZW",
                                "DEFLATE",
                                "NONE"
                            ]
                        },
                        "jpeg_quality": {
                            "type": "integer",
                            "description": "Set the JPEG quality when using JPEG.",
                            "minimum": 1,
                            "maximum": 100,
                            "default": 75
                        }
                    },
                    "links": [
                        {
                            "href": "https://gdal.org/drivers/raster/gtiff.html",
                            "rel": "about",
                            "title": "GDAL on the GeoTiff file format and storage options"
                        }
                    ]
                },
                "GeoJSON": {
                    "title": "GeoJSON",
                    "description": "Export to GeoJSON.",
                    "gis_data_types": [
                        "vector"
                    ],
                    "links": [
                        {
                            "href": "https://geojson.org/",
                            "rel": "about",
                            "title": "GeoJSON is a format for encoding a variety of geographic data structures."
                        }
                    ]
                },
            },
            "input": {
            }
        }
        # return {'input': [], 'output': ['GeoJSON']}

    def get_process(self, process_id: str) -> Process:
        for process in self.processes:
            if process.metadata['id'] == process_id:
                return process
        raise ValueError(f'Unknown process_id: {process_id}')

    def _add_default_processes(self):
        for dp in read_default_processes():
            self.add_process(dp)

    def _add_default_links(self):
        self.add_link({})


_PROCESS_REGISTRY_SINGLETON = None


def get_processes_registry() -> ProcessRegistry:
    """Return the process registry singleton."""
    global _PROCESS_REGISTRY_SINGLETON
    if not _PROCESS_REGISTRY_SINGLETON:
        _PROCESS_REGISTRY_SINGLETON = ProcessRegistry()
    return _PROCESS_REGISTRY_SINGLETON


def submit_process_sync(p: Process, ctx: ServerContextT) -> Any:
    """
    Submits a process synchronously, and returns the result.
    :param p: The process to execute.
    :param ctx: The Server context.
    :return: processing result
    """
    return p.execute(p.parameters, ctx)


class LoadCollection(Process):
    DEFAULT_CRS = 4326

    def execute(self, query_params: dict, ctx: ServerContextT):
        params = self.translate_parameters(query_params)
        collection_id = tuple(params['collection_id'].split('~'))
        bbox_transformed = None
        if params['bbox']:
            bbox = [float(v) for v in
                    params['bbox']
                    .replace('(', '')
                    .replace(')', '')
                    .replace(' ', '')
                    .split(',')]
            crs = int(params['crs'])
            bbox_transformed = ctx.transform_bbox(collection_id,
                                                  bbox, crs)

        return ctx.get_vector_cube(collection_id, bbox=bbox_transformed)

    def translate_parameters(self, query_params: dict) -> dict:
        bbox_qp = query_params['spatial_extent']['bbox'] \
            if ('spatial_extent' in query_params
                and query_params['spatial_extent']
                and 'bbox' in query_params['spatial_extent']) else None
        if not bbox_qp:
            crs_qp = None
        else:
            crs_qp = query_params['spatial_extent']['crs'] \
                if ('spatial_extent' in query_params
                    and query_params['spatial_extent']
                    and 'crs' in query_params['spatial_extent']) \
                else self.DEFAULT_CRS
        return {
            'collection_id': query_params['id'],
            'bbox': bbox_qp,
            'crs': crs_qp
        }


class AggregateTemporal(Process):

    def execute(self, query_params: dict, ctx: ServerContextT):
        # todo allow for more complex reducer functions
        # todo allow for more than one interval
        reducer_node = PGNode.from_flat_graph(query_params['reducer']
                                              ['process_graph'])
        reducer_id = reducer_node.process_id
        registry = get_processes_registry()
        reducer = registry.get_process(reducer_id)
        vector_cube = query_params['input']
        interval = query_params['intervals'][0]
        pattern = query_params['context']['pattern']
        utc = pytz.UTC
        start_date = (datetime.datetime.strptime(interval[0], pattern)
                      .replace(tzinfo=utc))
        end_date = (datetime.datetime.strptime(interval[1], pattern)
                    .replace(tzinfo=utc))
        time_dim_name = vector_cube.get_time_dim_name()
        features_by_geometry = vector_cube.get_features_by_geometry(limit=None)

        result = StaticVectorCubeFactory().copy(vector_cube, False,
                                                '_agg_temp')

        for geometry in features_by_geometry:
            features = features_by_geometry[geometry]
            extractions = {}
            for feature in features:
                for prop in [p for p in feature['properties'] if
                             not p == 'created_at'
                             and not p == 'modified_at'
                             and not p == time_dim_name
                             and (type(feature['properties'][p]) == float
                                  or type(feature['properties'][p]) == int)]:
                    if prop not in extractions:
                        extractions[prop] = []
                    date = (dateutil.parser.parse(
                        feature['properties'][time_dim_name]).replace(tzinfo=utc))
                    if start_date <= date < end_date:
                        extractions[prop].append(feature['properties'][prop])

            new_properties = {'created_at': datetime.datetime.now(utc),
                              time_dim_name: end_date}
            for prop in extractions.keys():
                new_properties[prop] = reducer.execute(
                    {'input': extractions[prop]}, ctx=ctx)
            for prop in feature['properties']:
                if prop not in new_properties:
                    new_properties[prop] = feature['properties'][prop]
            result.features.append(
                Feature(None, shapely.wkt.loads(geometry), new_properties))

        return result.create()


class SaveResult(Process):

    def execute(self, query_params: dict, ctx: ServerContextT):
        vector_cube = query_params['input']
        if query_params['format'].lower() == 'geojson':
            collection = FeatureCollection(
                vector_cube.load_features(limit=None, with_stac_info=False))
            return collection


class Mean(Process):

    def execute(self, query_params: dict, ctx: ServerContextT):
        import numpy as np
        return np.mean(query_params['input'])


class Std(Process):

    def execute(self, query_params: dict, ctx: ServerContextT):
        import numpy as np
        return np.std(query_params['input'])


class Median(Process):

    def execute(self, query_params: dict, ctx: ServerContextT):
        import numpy as np
        return np.median(query_params['input'])


class ArrayApply(Process):

    def execute(self, query_params: dict, ctx: ServerContextT) -> Any:
        graph = query_params['process']['process_graph']
        node = PGNode.from_flat_graph(graph)

        current_result = query_params['input']
        registry = get_processes_registry()
        process = registry.get_process(node.process_id)
        process_parameters = node.arguments
        process_parameters['input'] = current_result
        process.parameters = process_parameters
        current_result = submit_process_sync(process, ctx)

        return current_result


class Add(Process):

    def execute(self, query_params: dict, ctx: ServerContextT) -> Any:
        return execute_math_function(query_params, ctx, operator.add)


class Multiply(Process):

    def execute(self, query_params: dict, ctx: ServerContextT) -> VectorCube:
        return execute_math_function(query_params, ctx, operator.mul)


def execute_math_function(query_params: dict, ctx: ServerContextT,
                          op: Callable) -> VectorCube:
    current_result = query_params['input']
    y = query_params['y']
    if isinstance(y, dict) and 'process_graph' in y:
        process = get_next_process(current_result, y)
        result = basic_math_vc(current_result,
                               submit_process_sync(process, ctx),
                               op)
    elif isinstance(y, dict) and 'from_node' in y:
        process = get_prev_process(current_result, y)
        result = basic_math_vc(current_result,
                               submit_process_sync(process, ctx),
                               op)
    else:
        result = basic_math(current_result, y, op)
    return result

def basic_math(vc: VectorCube, v: [int, float], operation: Callable):
    result = (StaticVectorCubeFactory()
              .copy(vc, True)
              .create())
    features = result.load_features(limit=None,
                                    with_stac_info=False)
    time_dim_name = result.get_time_dim_name()
    for feature in features:
        for prop in [p for p in feature['properties'] if
                     not p == 'created_at'
                     and not p == 'modified_at'
                     and not p == time_dim_name
                     and (isinstance(feature['properties'][p], float)
                          or
                          isinstance(feature['properties'][p], int))]:
            feature['properties'][prop] = (
                operation(v, feature['properties'][prop]))
    return result


def basic_math_vc(a: VectorCube, b: VectorCube, operation: Callable) \
        -> VectorCube:
    result = (StaticVectorCubeFactory()
              .copy(a, True)
              .create())
    features = result.load_features(limit=None, with_stac_info=False)
    time_dim_name = result.get_time_dim_name()
    for feature in features:
        for prop in [p for p in feature['properties'] if
                     not p == 'created_at'
                     and not p == 'modified_at'
                     and not p == time_dim_name
                     and (isinstance(feature['properties'][p], float)
                          or isinstance(feature['properties'][p], int))]:
            feature_b = b.get_feature(feature['id'])
            feature['properties'][prop] = (
                operation(feature['properties'][prop],
                           feature_b['properties'][prop]))
    return result


def get_next_process(current_result, y) -> Process:
    sub_graph = y['process_graph']
    node = PGNode.from_flat_graph(sub_graph)
    registry = get_processes_registry()
    process = registry.get_process(node.process_id)
    process_parameters = node.arguments
    process_parameters['input'] = current_result
    process.parameters = process_parameters
    return process


def get_prev_process(current_result, y) -> Process:
    node = y['from_node']
    registry = get_processes_registry()
    process = registry.get_process(node.process_id)
    process_parameters = node.arguments
    process_parameters['input'] = current_result
    process.parameters = process_parameters
    return process
