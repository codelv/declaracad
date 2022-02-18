"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCCT.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Wire

from declaracad.occ.shape import ProxyFace

from .occ_shape import OccDependentShape, OccShape
from .topology import Topology


def shape_to_face(shape):
    if isinstance(shape, OccShape):
        shape = shape.shape
    shape = Topology.cast_shape(shape)
    if isinstance(shape, (TopoDS_Face, TopoDS_Wire)):
        return shape
    if isinstance(shape, TopoDS_Edge):
        return BRepBuilderAPI_MakeWire(shape).Wire()
    return TopoDS.Wire_(shape)


class OccFace(OccDependentShape, ProxyFace):
    def update_shape(self, change=None):
        d = self.declaration
        if d.wires:
            shapes = d.wires
        else:
            shapes = [c for c in self.children() if isinstance(c, OccShape)]
        if not shapes:
            raise ValueError("No wires or children available to create a face!")

        for i, s in enumerate(shapes):
            if i == 0:
                shape = BRepBuilderAPI_MakeFace(shape_to_face(s))
            else:
                shape.Add(shape_to_face(s))
        self.shape = shape.Face()

    def set_wires(self, wires):
        self.update_shape()
