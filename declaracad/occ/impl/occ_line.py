"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Typed, set_default

from OCCT.Geom import Geom_Line
from OCCT.GC import GC_MakeLine
from OCCT.gp import gp_Lin, gp_Vec

from declaracad.occ.draw import ProxyLine
from .occ_edge import OccEdge, LINE_TYPES
from .occ_shape import coerce_axis


class OccLine(OccEdge, ProxyLine):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/" "classgp___lin.html"
    )

    curve = Typed(Geom_Line)

    def get_transformed_points(self, points=None):
        d = self.declaration
        t = self.get_transform()
        return [p.proxy.Transformed(t) for p in points or d.points]

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        if n == 2:
            curve = GC_MakeLine(*self.get_transformed_points()).Value()
        elif n == 1:
            lin = gp_Lin(d.position.proxy, gp_Vec(d.direction.proxy))
            offset_point = self.get_transformed_points()
            curve = GC_MakeLine(lin, offset_point).Value()
        else:
            axis = coerce_axis(d.axis)
            curve = GC_MakeLine(axis.Axis()).Value()
        self.curve = curve
        self.shape = self.make_edge(curve)

    def set_points(self, points):
        self.create_shape()
