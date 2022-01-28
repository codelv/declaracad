"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from OCCT.BRep import BRep_Builder
from OCCT.BRepOffsetAPI import BRepOffsetAPI_NormalProjection
from OCCT.TopoDS import TopoDS_Compound

from declaracad.occ.algo import ProxyNormalProjection

from .occ_algo import OccOperation, coerce_shape
from .topology import Topology


class OccNormalProjection(OccOperation, ProxyNormalProjection):
    def update_shape(self, change=None):
        d = self.declaration

        shapes = list(self.child_shapes())
        if d.shape:
            shapes_to_project = shapes
            face = coerce_shape(d.shape)
        else:
            face = shapes[0]
            shapes_to_project = shapes[1:]

        projection = BRepOffsetAPI_NormalProjection(face)
        if d.max_distance:
            projection.SetMaxDistance(d.max_distance)
        for shape in shapes_to_project:
            projection.Add(shape)

        projection.Build()
        if not projection.IsDone():
            raise RuntimeError(f"Could not project wire onto face {d}")

        # Create a compound of wires
        topo = Topology(shape=projection.Shape())
        shape = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(shape)
        for wire in Topology.join_edges(topo.edges):
            builder.Add(shape, wire)

        self.shape = shape

    def set_max_distance(self, distance):
        self.update_shape()

    def set_shape(self, shape):
        self.update_shape()
