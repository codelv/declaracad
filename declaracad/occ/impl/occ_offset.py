"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCCT.BRepOffset import BRepOffset_Pipe, BRepOffset_RectoVerso, BRepOffset_Skin
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MakeOffset, BRepOffsetAPI_MakeOffsetShape
from OCCT.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection, GeomAbs_Tangent
from OCCT.TopoDS import TopoDS_Compound, TopoDS_Edge, TopoDS_Face, TopoDS_Wire

from declaracad.occ.algo import ProxyOffset, ProxyOffsetShape

from .occ_algo import OccOperation, coerce_shape
from .topology import Topology


class OccOffset(OccOperation, ProxyOffset):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___make_offset.html"
    )

    offset_modes = {
        "skin": BRepOffset_Skin,
        "pipe": BRepOffset_Pipe,
        "recto_verso": BRepOffset_RectoVerso,
    }

    join_types = {
        "arc": GeomAbs_Arc,
        "tangent": GeomAbs_Tangent,
        "intersection": GeomAbs_Intersection,
    }

    def get_shape_to_offset(self):
        d = self.declaration
        if d.shape:
            return coerce_shape(d.shape)
        return self.get_first_child().shape

    def update_shape(self, change=None):
        d = self.declaration
        shape = Topology.cast_shape(self.get_shape_to_offset())
        if isinstance(shape, TopoDS_Edge):
            shape = BRepBuilderAPI_MakeWire(shape).Wire()
        elif isinstance(shape, TopoDS_Compound):
            topo = Topology(shape=shape)
            first, *others = topo.faces
            builder = BRepBuilderAPI_MakeFace(first)
            for face in others:
                builder.Add(face)
            shape = builder.Face()
        elif not isinstance(shape, (TopoDS_Wire, TopoDS_Face)):
            t = type(shape)
            raise TypeError(f"Unsupported child shape {t} when using planar mode")
        join_type = self.join_types[d.join_type]
        offset_shape = BRepOffsetAPI_MakeOffset(shape, join_type, not d.closed)
        offset_shape.Perform(d.offset, d.normal_distance)
        if not offset_shape.IsDone():
            # Note: Lines cannot be offset as they have no plane of reference
            raise ValueError("Could not perform offset: %s" % d)

        result = Topology.cast_shape(offset_shape.Shape())
        if d.as_face:
            if isinstance(result, TopoDS_Compound):
                topo = Topology(shape=result)
                first, *others = topo.wires
                builder = BRepBuilderAPI_MakeFace(first)
                for face in others:
                    builder.Add(face)
                self.shape = builder.Face()
            else:
                self.shape = BRepBuilderAPI_MakeFace(result).Face()
        else:
            self.shape = result

    def set_shape(self, shape):
        self.update_shape()

    def set_offset(self, offset):
        self.update_shape()

    def set_offset_mode(self, mode):
        self.update_shape()

    def set_join_type(self, mode):
        self.update_shape()

    def set_intersection(self, enabled):
        self.update_shape()

    def set_as_face(self, enabled: bool):
        self.update_shape()


class OccOffsetShape(OccOffset, ProxyOffsetShape):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___make_offset_shape.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        shape = self.get_shape_to_offset()
        offset_shape = BRepOffsetAPI_MakeOffsetShape()
        offset_shape.PerformByJoin(
            shape,
            d.offset,
            d.tolerance,
            self.offset_modes[d.offset_mode],
            d.intersection,
            False,
            self.join_types[d.join_type],
        )
        self.shape = offset_shape.Shape()
