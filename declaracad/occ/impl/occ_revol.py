"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from OCCT.BRepPrimAPI import BRepPrimAPI_MakeRevol
from OCCT.gp import gp_Ax1

from declaracad.occ.shape import ProxyRevol

from .occ_shape import OccDependentShape, coerce_shape


class OccRevol(OccDependentShape, ProxyRevol):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_wedge.html"
    )

    def update_shape(self, change=None):
        d = self.declaration

        if d.shape:
            shape = coerce_shape(d.shape)
            copy = True
        else:
            shape = self.get_first_child().shape
            copy = False

        #: Build arguments
        args = [shape, gp_Ax1(d.position.proxy, d.direction.proxy)]
        if d.angle:
            args.append(d.angle)
        args.append(copy)

        revol = BRepPrimAPI_MakeRevol(*args)
        self.shape = revol.Shape()

    def set_shape(self, shape):
        self.update_shape()

    def set_angle(self, angle):
        self.update_shape()

    def set_copy(self, copy):
        self.update_shape()

    def set_direction(self, direction):
        self.update_shape()
