"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Typed, set_default

from OCCT.Geom import Geom_Parabola

from declaracad.occ.draw import ProxyParabola
from .occ_edge import OccEdge
from .occ_shape import coerce_axis


class OccParabola(OccEdge, ProxyParabola):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/classgp___parab.html"
    )

    curve = Typed(Geom_Parabola)

    def create_shape(self):
        d = self.declaration
        curve = self.curve = Geom_Parabola(coerce_axis(d.axis), d.focal_length)
        self.shape = self.make_edge(curve)

    def set_focal_length(self, l):
        self.create_shape()
