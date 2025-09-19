"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import Typed
from OCCT.Aspect import (
    Aspect_TOL_DASH,
    Aspect_TOL_DOT,
    Aspect_TOL_DOTDASH,
    Aspect_TOL_SOLID,
)
from OCCT.BRep import BRep_Tool
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire
from OCCT.Geom import Geom_TrimmedCurve
from OCCT.GeomAPI import GeomAPI
from OCCT.gp import gp_Pln

from declaracad.occ.draw import ProxyEdge

from .occ_shape import OccShape
from .topology import Topology

LINE_TYPES = {
    "solid": Aspect_TOL_SOLID,
    "dashed": Aspect_TOL_DASH,
    "dotted": Aspect_TOL_DOT,
    "dot_dash": Aspect_TOL_DOTDASH,
}


class OccEdge(OccShape, ProxyEdge):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_edge.html"
    )

    curve = Typed(Geom_TrimmedCurve)

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        if d.line_style != "solid":
            type_of_line = LINE_TYPES[d.line_style]
            if d.as_wire:
                ais_shape.Attributes().WireAspect().SetTypeOfLine(type_of_line)
            else:
                ais_shape.Attributes().LineAspect().SetTypeOfLine(type_of_line)
        if d.line_width > 0:
            ais_shape.SetWidth(d.line_width)
        return ais_shape

    def make_edge(self, *args):
        d = self.declaration
        if d.surface:
            # Convert the curve to 2d
            args = list(args)
            pln = gp_Pln(d.position.proxy, d.direction.proxy)
            args[0] = GeomAPI.To2d_(args[0], pln)
            args.insert(1, BRep_Tool.Surface_(d.surface))
        edge = BRepBuilderAPI_MakeEdge(*args).Edge()
        if d.as_wire:
            return BRepBuilderAPI_MakeWire(edge).Wire()
        return edge

    def get_value_at(self, t, derivative=0):
        if self.curve is None:
            self.create_shape()
        return Topology.get_value_at(self.curve, t, derivative)

    def set_surface(self, surface):
        self.create_shape()

    def set_as_wire(self, enabled):
        self.create_shape()

    def set_reverse(self, reverse):
        self.create_shape()
