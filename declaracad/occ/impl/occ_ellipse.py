"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import Typed
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCCT.Geom import Geom_Ellipse

from declaracad.occ.draw import ProxyEllipse

from .occ_edge import OccEdge
from .occ_shape import coerce_axis


class OccEllipse(OccEdge, ProxyEllipse):
    #: Update the class reference
    reference = "https://dev.opencascade.org/doc/refman/html/classgp___elips.html"

    curve = Typed(Geom_Ellipse)

    def create_shape(self):
        d = self.declaration
        major = max(d.major_radius, d.minor_radius)
        minor = min(d.major_radius, d.minor_radius)
        curve = self.curve = Geom_Ellipse(coerce_axis(d.axis), major, minor)
        edge = self.make_edge(curve)
        if d.as_face:
            wire = BRepBuilderAPI_MakeWire(edge).Wire()
            self.shape = BRepBuilderAPI_MakeFace(wire).Face()
        elif d.as_wire:
            self.shape = BRepBuilderAPI_MakeWire(edge).Wire()
        else:
            self.shape = edge

    def set_major_radius(self, r):
        self.create_shape()

    def set_minor_radius(self, r):
        self.create_shape()
