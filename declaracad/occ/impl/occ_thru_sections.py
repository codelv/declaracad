"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""

from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCCT.BRepOffsetAPI import BRepOffsetAPI_ThruSections
from OCCT.BRepTools import BRepTools
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Vertex, TopoDS_Wire

from declaracad.occ.algo import ProxyThruSections, Shape

from .occ_algo import OccOperation


class OccThruSections(OccOperation, ProxyThruSections):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___thru_sections.html"
    )

    def add_to_loft(self, loft: BRepOffsetAPI_ThruSections, item):
        if isinstance(item, Shape):
            s = item.proxy.shape
        else:
            s = item
        if isinstance(s, TopoDS_Vertex):
            loft.AddVertex(s)
        elif isinstance(s, TopoDS_Edge):
            loft.AddWire(BRepBuilderAPI_MakeWire(s).Wire())
        elif isinstance(s, TopoDS_Wire):
            loft.AddWire(s)
        elif isinstance(s, TopoDS_Face):
            loft.AddWire(BRepTools.OuterWire_(s))
        else:
            raise ValueError(f"Cannot use {s} for loft section {self.declaration}")

    def update_shape(self, change=None):
        d = self.declaration
        loft = BRepOffsetAPI_ThruSections(d.solid, d.ruled, d.precision)
        # loft.CheckCompatibility(True)
        #: TODO: Support Smoothing, Max degree, par type, etc...
        for section in d.sections:
            self.add_to_loft(loft, section)
        for child in self.children():
            self.add_to_loft(loft, child.shape)

        #: Set the shape
        shape = loft.Shape()
        if d.fix:
            fixer = ShapeFix_Shape(shape)
            if fixer.Perform():
                shape = fixer.Shape()
        self.shape = shape

    def set_solid(self, solid):
        self.update_shape()

    def set_sections(self, sections):
        self.update_shape()

    def set_ruled(self, ruled):
        self.update_shape()

    def set_fix(self, fix):
        self.update_shape()

    def set_precision(self, pres3d):
        self.update_shape()
