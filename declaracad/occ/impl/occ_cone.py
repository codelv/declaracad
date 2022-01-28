"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeCone

from declaracad.occ.shape import ProxyCone

from .occ_shape import OccShape, coerce_axis


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
        cone = BRepPrimAPI_MakeCone(*args)
        self.shape = cone.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_height(self, height):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()
