"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Typed
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)
from OCCT.GC import GC_MakeArcOfEllipse
from OCCT.gp import gp_Pnt
from OCCT.TopoDS import TopoDS

from declaracad.occ.draw import ProxyRectangle

from .occ_svg import make_ellipse
from .occ_wire import OccWire


class OccRectangle(OccWire, ProxyRectangle):
    curve = Typed(BRepAdaptor_CompCurve)

    def create_shape(self):
        d = self.declaration
        t = self.get_transform()
        w, h = d.width, d.height
        if d.rx or d.ry:
            rx, ry = d.rx, d.ry
            if not ry:
                ry = rx
            elif not rx:
                rx = ry

            # Clamp to the valid range
            rx = min(w / 2, rx)
            ry = min(h / 2, ry)

            # Bottom
            p1 = gp_Pnt(0 + rx, 0, 0)
            p2 = gp_Pnt(0 + w - rx, 0, 0)

            # Right
            p3 = gp_Pnt(w, ry, 0)
            p4 = gp_Pnt(w, h - ry, 0)

            # Top
            p5 = gp_Pnt(w - rx, h, 0)
            p6 = gp_Pnt(rx, h, 0)

            # Left
            p7 = gp_Pnt(0, h - ry, 0)
            p8 = gp_Pnt(0, ry, 0)

            shape = BRepBuilderAPI_MakeWire()

            e = d.tolerance

            # Bottom
            if not p1.IsEqual(p2, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p1, p2).Edge())

            # Arc bottom right
            c = make_ellipse((w - rx, ry, 0), rx, ry)
            shape.Add(
                BRepBuilderAPI_MakeEdge(
                    GC_MakeArcOfEllipse(c, p2, p3, False).Value()
                ).Edge()
            )

            # Right
            if not p3.IsEqual(p4, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p3, p4).Edge())

            # Arc top right
            c.SetLocation(gp_Pnt(w - rx, h - ry, 0))
            shape.Add(
                BRepBuilderAPI_MakeEdge(
                    GC_MakeArcOfEllipse(c, p4, p5, False).Value()
                ).Edge()
            )

            # Top
            if not p5.IsEqual(p6, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p5, p6).Edge())

            # Arc top left
            c.SetLocation(gp_Pnt(rx, h - ry, 0))
            shape.Add(
                BRepBuilderAPI_MakeEdge(
                    GC_MakeArcOfEllipse(c, p6, p7, False).Value()
                ).Edge()
            )

            # Left
            if not p7.IsEqual(p8, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p7, p8).Edge())

            # Arc bottom left
            c.SetLocation(gp_Pnt(rx, ry, 0))
            shape.Add(
                BRepBuilderAPI_MakeEdge(
                    GC_MakeArcOfEllipse(c, p8, p1, False).Value()
                ).Edge()
            )

            shape = shape.Wire()
            shape.Closed(True)
        else:
            shape = BRepBuilderAPI_MakePolygon(
                gp_Pnt(0, 0, 0), gp_Pnt(w, 0, 0), gp_Pnt(w, h, 0), gp_Pnt(0, h, 0), True
            ).Wire()
        wire = TopoDS.Wire_(BRepBuilderAPI_Transform(shape, t, False).Shape())
        self.curve = BRepAdaptor_CompCurve(wire)
        self.shape = wire

    def update_shape(self, change=None):
        self.create_shape()

    def init_layout(self):
        # This does not depened on children
        pass
