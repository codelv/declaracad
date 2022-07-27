"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on July 22, 2022

@author: jrm
"""
from atom.api import (
    Atom,
    Coerced,
    Enum,
    Float,
    ForwardTyped,
    Int,
    List,
    Tuple,
    Typed,
    Value,
    observe,
)
from enaml.core.declarative import d_

from .shape import Point, ProxyShape, Shape, coerce_point


class ProxyVoxel(ProxyShape):
    #: Reference to the declaration
    declaration = ForwardTyped(lambda: Voxel)

    def set_source(self, source):
        raise NotImplementedError

    def set_deflection(self, deflection: float):
        raise NotImplementedError

    def set_splits(self, splits: tuple):
        raise NotImplementedError

    def set_threads(self, threads: int):
        raise NotImplementedError

    def set_mode(self, mode: str):
        raise NotImplementedError


class ProxyVoxelTopology(Atom):
    #: Reference to the mesh
    declaration = ForwardTyped(lambda: Voxel)


class Voxel(Shape):
    #: Reference to the proxy
    proxy = Typed(ProxyVoxel)

    #: If provided, convert the shape into a voxel
    source = d_(Value())

    #: Deflection
    deflection = d_(Float(0.1))

    #: Bounds
    bounds = d_(List(Coerced(Point, coercer=coerce_point)))

    #: Voxel data source mode
    mode = d_(Enum("octree", "bool", "color"))

    #: Number of x, y, z voxels
    splits = d_(Tuple(int))

    #: Threads
    threads = d_(Int(1))

    #: Fill value
    fill = d_(Int(1))

    @observe("source", "deflection", "domain", "splits", "threads", "mode")
    def _update_proxy(self, change):
        super()._update_proxy(change)
