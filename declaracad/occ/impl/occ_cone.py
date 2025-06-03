"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from typing import Optional

from atom.api import set_default
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeCone
from OCCT.TopoDS import TopoDS_Face

from declaracad.occ.geom import Point
from declaracad.occ.shape import ProxyCone

from .occ_shape import OccShape, coerce_axis
from .topology import Topology


class OccCone(OccShape, ProxyCone):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_cone.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.radius2, d.height]
        if d.angle:
            args.append(d.angle)
        builder = BRepPrimAPI_MakeCone(*args)
        self.shape = builder.Shape()

    def set_radius(self, r: float):
        self.create_shape()

    def set_radius2(self, r: float):
        self.create_shape()

    def set_height(self, height: float):
        self.create_shape()

    def set_angle(self, a: float):
        self.create_shape()

    def get_apex(self) -> Point:
        if self.shape is None:
            self.create_shape()
        f: Optional[TopoDS_Face] = None
        for f in self.declaration.topology.faces:
            if Topology.is_cone(f):
                break
        assert f is not None
        surface = Topology.cast_surface(f)
        assert surface is not None
        return Point(surface.Apex())
