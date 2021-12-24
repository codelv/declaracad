"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from OCCT.BRepOffsetAPI import BRepOffsetAPI_NormalProjection

from declaracad.occ.algo import ProxyNormalProjection
from .occ_algo import OccOperation, coerce_shape
from .topology import Topology


class OccNormalProjection(OccOperation, ProxyNormalProjection):
    def update_shape(self, change=None):
        d = self.declaration

        shapes_to_project = self.child_shapes()
        if d.shape:
            face = coerce_shape(d.shape)
        else:
            face, *shapes_to_project = shapes_to_project[0], shapes_to_project[1:]
        projection = BRepOffsetAPI_NormalProjection(face)
        if d.max_distance:
            projection.SetMaxDistance(d.max_distance)
        for shape in shapes_to_project:
            projection.Add(shape)

        projection.Build()
        if not projection.IsDone():
            raise RuntimeError(f"Could not project wire onto face {d}")

        self.shape = Topology.cast_shape(projection.Shape())

    def set_max_distance(self, distance):
        self.update_shape()

    def set_shape(self, shape):
        self.update_shape()
