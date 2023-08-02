"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Typed, set_default
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_Transform,
)
from OCCT.TopoDS import TopoDS

from declaracad.occ.draw import ProxyPolyline
from declaracad.core.utils import log

from .occ_wire import OccWire


class OccPolyline(OccWire, ProxyPolyline):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_polygon.html"
    )

    curve = Typed(BRepAdaptor_CompCurve)

    def create_shape(self):
        d = self.declaration
        t = self.get_transform()
        shape = BRepBuilderAPI_MakePolygon()
        for p in d.points:
            shape.Add(p.proxy)
        if d.closed:
            shape.Close()
        try:
            builder = BRepBuilderAPI_Transform(shape.Wire(), t, False)
        except RuntimeError as e:
            log.error(f"Could not create polyline from {d.points}")
            raise e
        wire = TopoDS.Wire_(builder.Shape())
        curve = self.curve = BRepAdaptor_CompCurve(wire)
        wire = curve.Wire()
        if d.as_face:
            self.shape = BRepBuilderAPI_MakeFace(wire).Face()
        else:
            self.shape = wire

    def init_layout(self):
        # This does not depened on children
        pass

    def update_shape(self, change=None):
        self.create_shape()

    def set_closed(self, closed: bool):
        self.create_shape()

    def set_as_wire(self, as_wire: bool):
        self.create_shape()
