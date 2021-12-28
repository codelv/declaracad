"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from math import pi
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeSphere

from declaracad.occ.shape import ProxySphere
from .occ_shape import OccShape, coerce_axis


class OccSphere(OccShape, ProxySphere):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_sphere.html"
    )

    def create_shape(self):
        d = self.declaration
        u = min(2 * pi, max(0, d.angle))
        vmin = max(-pi / 2, min(d.angle2, d.angle3))
        vmax = min(pi / 2, max(d.angle2, d.angle3))
        axis = coerce_axis(d.axis)
        sphere = BRepPrimAPI_MakeSphere(axis, d.radius, vmin, vmax, u)
        self.shape = sphere.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()

    def set_angle2(self, a):
        self.create_shape()

    def set_angle3(self, a):
        self.create_shape()
