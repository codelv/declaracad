"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""

from atom.api import set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCCT.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.TopoDS import TopoDS_Edge, TopoDS_Vertex, TopoDS_Wire

from declaracad.occ.algo import ProxyThruSections

from .occ_algo import OccOperation


class OccThruSections(OccOperation, ProxyThruSections):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___thru_sections.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        loft = BRepOffsetAPI_ThruSections(d.solid, d.ruled, d.precision)
        # loft.CheckCompatibility(True)
        #: TODO: Support Smoothing, Max degree, par type, etc...

        for child in self.children():
            s = child.shape
            if isinstance(s, TopoDS_Vertex):
                loft.AddVertex(s)
            elif isinstance(s, TopoDS_Edge):
                loft.AddWire(BRepBuilderAPI_MakeWire(s).Wire())
            elif isinstance(s, TopoDS_Wire):
                loft.AddWire(s)

        #: Set the shape
        shape = loft.Shape()
        if d.fix:
            fixer = ShapeFix_Shape(shape)
            if fixer.Perform():
                shape = fixer.Shape()
        self.shape = shape

    def set_solid(self, solid):
        self.update_shape()

    def set_ruled(self, ruled):
        self.update_shape()

    def set_fix(self, fix):
        self.update_shape()

    def set_precision(self, pres3d):
        self.update_shape()
