"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeBox

from declaracad.occ.shape import ProxyBox

from .occ_shape import OccShape, coerce_axis


class OccBox(OccShape, ProxyBox):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_box.html"
    )

    def create_shape(self):
        d = self.declaration
        box = BRepPrimAPI_MakeBox(coerce_axis(d.axis), d.dx, d.dy, d.dz)
        self.shape = box.Shape()

    def set_dx(self, dx):
        self.create_shape()

    def set_dy(self, dy):
        self.create_shape()

    def set_dz(self, dz):
        self.create_shape()
