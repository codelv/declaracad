"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import set_default
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeCylinder

from declaracad.occ.shape import ProxyCylinder

from .occ_shape import OccShape, coerce_axis


class OccCylinder(OccShape, ProxyCylinder):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_cylinder.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.height]
        if d.angle:
            args.append(d.angle)
        cylinder = BRepPrimAPI_MakeCylinder(*args)
        self.shape = cylinder.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_angle(self, angle):
        self.create_shape()

    def set_height(self, height):
        self.create_shape()
