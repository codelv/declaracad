"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from OCCT import TopoDS
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCCT.ShapeFix import ShapeFix_Face
from OCCT.TopoDS import TopoDS_Compound, TopoDS_Edge, TopoDS_Face, TopoDS_Wire

from declaracad.occ.shape import ProxyFace

from .occ_shape import OccDependentShape, OccShape
from .topology import Topology


def shape_to_wire(shape) -> TopoDS_Wire:
    if isinstance(shape, OccShape):
        shape = shape.shape
    shape = Topology.cast_shape(shape)
    if isinstance(shape, (TopoDS_Face, TopoDS_Wire)):
        return shape
    if isinstance(shape, TopoDS_Edge):
        return BRepBuilderAPI_MakeWire(shape).Wire()
    if isinstance(shape, TopoDS_Compound):
        topo = Topology(shape=shape)
        if len(topo.faces) == 1:
            return topo.faces[0]
        if len(topo.wires) == 1:
            return topo.wires[0]
        raise ValueError(f"Cannot convert compound {shape} to face")
    return TopoDS.Wire(shape)


class OccFace(OccDependentShape, ProxyFace):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_face.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        if d.wires:
            shapes = d.wires
        else:
            shapes = [c for c in self.children() if isinstance(c, OccShape)]
        if not shapes:
            raise ValueError("No wires or children available to create a face!")

        if d.surface:
            if len(shapes) > 1:
                raise ValueError("Only 1 wire can be used when a surface is given!")
            shape = BRepBuilderAPI_MakeFace(
                d.surface,
                shape_to_wire(shapes[0])
            )
        else:
            for i, s in enumerate(shapes):
                if i == 0:
                    shape = BRepBuilderAPI_MakeFace(shape_to_wire(s))
                else:
                    shape.Add(shape_to_wire(s))

        face = shape.Face()
        if d.fix:
            fixer = ShapeFix_Face(face)
            if fixer.Perform():
                face = fixer.Face()
        self.shape = face

    def set_wires(self, wires):
        self.update_shape()
