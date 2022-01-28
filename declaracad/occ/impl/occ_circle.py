"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Typed, set_default
from OCCT.Geom import Geom_Circle

from declaracad.occ.draw import ProxyCircle

from .occ_edge import OccEdge
from .occ_shape import coerce_axis


class OccCircle(OccEdge, ProxyCircle):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/classgp___circ.html"
    )

    curve = Typed(Geom_Circle)

    def create_shape(self):
        d = self.declaration
        curve = self.curve = Geom_Circle(coerce_axis(d.axis), abs(d.radius))
        self.shape = self.make_edge(curve)

    def set_radius(self, r):
        self.create_shape()
