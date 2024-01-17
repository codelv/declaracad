"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeTorus

from declaracad.occ.shape import ProxyTorus

from .occ_shape import OccShape, coerce_axis


class OccTorus(OccShape, ProxyTorus):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_torus.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.radius2]
        if d.angle2 or d.angle3:
            amin = min(d.angle2, d.angle3)
            amax = max(d.angle2, d.angle3)
            args.append(amin)
            args.append(amax)
        if d.angle:
            args.append(d.angle)
        torus = BRepPrimAPI_MakeTorus(*args)
        self.shape = torus.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()

    def set_angle2(self, a):
        self.create_shape()

    def set_angle3(self, a):
        self.create_shape()
