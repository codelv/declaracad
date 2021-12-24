"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Typed, set_default

from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakePolygon

from declaracad.occ.draw import ProxyPolyline
from .occ_wire import OccWire


class OccPolyline(OccWire, ProxyPolyline):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_polygon.html')

    curve = Typed(BRepAdaptor_CompCurve)

    def create_shape(self):
        d = self.declaration
        t = self.get_transform()
        shape = BRepBuilderAPI_MakePolygon()
        for p in d.points:
            shape.Add(p.proxy.Transformed(t))
        if d.closed:
            shape.Close()
        curve = self.curve = BRepAdaptor_CompCurve(shape.Wire())
        self.shape = curve.Wire()

    def init_layout(self):
        # This does not depened on children
        pass

    def update_shape(self, change=None):
        self.create_shape()

    def set_closed(self, closed):
        self.create_shape()
