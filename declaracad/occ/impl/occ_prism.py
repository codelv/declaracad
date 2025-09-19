"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from OCCT.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCCT.gp import gp_Vec

from declaracad.occ.shape import ProxyPrism

from .occ_shape import OccDependentShape, coerce_shape


class OccPrism(OccDependentShape, ProxyPrism):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_prism.html"
    )

    def update_shape(self, change=None):
        d = self.declaration

        if d.shape:
            shape = coerce_shape(d.shape)
            copy = True
        else:
            shape = self.get_first_child().shape
            copy = False

        if d.infinite:
            args = (shape, d.direction.proxy, True, copy, d.canonize)
        else:
            args = (shape, gp_Vec(*d.vector), copy, d.canonize)
        prism = BRepPrimAPI_MakePrism(*args)
        self.shape = prism.Shape()

    def set_shape(self, shape):
        self.update_shape()

    def set_infinite(self, infinite):
        self.update_shape()

    def set_copy(self, copy):
        self.update_shape()

    def set_canonize(self, canonize):
        self.update_shape()

    def set_direction(self, direction):
        self.update_shape()

    def set_vector(self, vector):
        self.update_shape()
