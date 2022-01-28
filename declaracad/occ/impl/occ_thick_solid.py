"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from atom.api import set_default
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MakeThickSolid
from OCCT.TopoDS import TopoDS_Shape
from OCCT.TopTools import TopTools_ListOfShape

from declaracad.occ.algo import ProxyThickSolid

from .occ_offset import OccOffset
from .topology import Topology


class OccThickSolid(OccOffset, ProxyThickSolid):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___make_thick_solid.html"
    )

    def get_faces(self, occ_shape):
        d = self.declaration
        if d.faces:
            return d.faces

        if isinstance(occ_shape, TopoDS_Shape):
            topology = Topology(shape=occ_shape)
        else:
            topology = occ_shape.topology

        for face in topology.faces:
            return [face]

    def update_shape(self, change=None):
        d = self.declaration
        shape = self.get_shape_to_offset()
        faces = TopTools_ListOfShape()
        for f in self.get_faces(shape):
            faces.Append(f)
        assert not faces.IsEmpty()

        offset_mode = self.offset_modes[d.offset_mode]
        join_type = self.join_types[d.join_type]

        thick_solid = BRepOffsetAPI_MakeThickSolid()
        thick_solid.MakeThickSolidByJoin(
            shape,
            faces,
            d.offset,
            d.tolerance,
            offset_mode,
            d.intersection,
            False,
            join_type,
        )
        self.shape = thick_solid.Shape()

    def set_faces(self, faces):
        self.update_shape()
