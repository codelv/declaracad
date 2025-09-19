"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import Typed
from OCCT.BRep import BRep_Tool
from OCCT.Geom import Geom_TrimmedCurve

from declaracad.occ.draw import ProxyTrimmedCurve

from .occ_edge import OccEdge
from .occ_shape import OccShape
from .topology import Shape, Topology


class OccTrimmedCurve(OccEdge, ProxyTrimmedCurve):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/class_geom___trimmed_curve.html"
    )

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        pass

    def init_layout(self):
        self.update_shape()
        for child in self.children():
            if not isinstance(child, OccShape):
                continue
            child.observe("shape", self.update_shape)

    def update_shape(self, change=None):
        d = self.declaration
        shape = d.shape
        if shape is None:
            child = self.get_first_child()
            if hasattr(child, "curve"):
                curve = child.curve
            else:
                curve = BRep_Tool.Curve_(child.shape, 0, 1)[0]
        else:
            if isinstance(shape, Shape) and hasattr(shape.proxy, "curve"):
                curve = shape.proxy.curve
            else:
                curve = BRep_Tool.Curve_(shape, 0, 1)[0]
        if curve is None:
            curve = Topology.cast_curve(shape)
        if curve is None:
            raise RuntimeError(f"Could not create TrimmedCurve {d} (no curve)")
        trimmed_curve = self.curve = Geom_TrimmedCurve(curve, d.u, d.v)
        self.shape = self.make_edge(trimmed_curve)

    def set_u(self, u):
        self.update_shape()

    def set_v(self, v):
        self.update_shape()
