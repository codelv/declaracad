"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Typed, set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCCT.Geom import Geom_Plane
from OCCT.gp import gp_Pln

from declaracad.occ.draw import ProxyPlane

from .occ_shape import OccShape


class OccPlane(OccShape, ProxyPlane):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/classgp___pnt.html"
    )

    curve = Typed(Geom_Plane)

    def create_shape(self):
        d = self.declaration
        pln = gp_Pln(d.position.proxy, d.direction.proxy)

        curve = self.curve = Geom_Plane(pln)
        if d.bounds:
            u, v = d.bounds
            face = BRepBuilderAPI_MakeFace(pln, u.x, v.x, u.y, v.y)
        else:
            face = BRepBuilderAPI_MakeFace(pln)

        self.shape = face.Face()

    def set_bounds(self, bounds):
        self.create_shape()
