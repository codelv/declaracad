"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default

from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
from OCCT.gp import gp_Pln

from declaracad.occ.shape import ProxyHalfSpace
from .occ_shape import OccDependentShape, coerce_axis


class OccHalfSpace(OccDependentShape, ProxyHalfSpace):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_half_space.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        if d.surface:
            surface = d.surface
        else:
            child = self.get_first_child()
            if child:
                surface = child.shape
            else:
                pln = gp_Pln(d.position.proxy, d.direction.proxy)
                surface = BRepBuilderAPI_MakeFace(pln).Face()
        half_space = BRepPrimAPI_MakeHalfSpace(surface, d.side.proxy)
        # Shape doesnt work see
        # https://tracker.dev.opencascade.org/view.php?id=29969
        self.shape = half_space.Solid()

    def set_surface(self, surface):
        self.update_shape()

    def set_side(self, side):
        self.update_shape()
