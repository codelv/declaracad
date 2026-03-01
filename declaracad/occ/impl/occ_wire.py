"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""

from atom.api import Typed
from OCCT.BRepAdaptor import (
    BRepAdaptor_CompCurve,
    BRepAdaptor_Curve2d,
    BRepAdaptor_Surface,
)
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_FindPlane,
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
)
from OCCT.BRepLib import BRepLib
from OCCT.ShapeFix import ShapeFix_Wire
from OCCT.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Wire
from OCCT.TopTools import TopTools_ListOfShape

from declaracad.core.utils import log
from declaracad.occ.draw import ProxyWire

from .occ_edge import LINE_TYPES
from .occ_shape import OccDependentShape, OccShape
from .topology import Topology


class OccWire(OccDependentShape, ProxyWire):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_wire.html"
    )

    curve = Typed(BRepAdaptor_CompCurve)

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        if d.line_style != "solid":
            type_of_line = LINE_TYPES[d.line_style]
            ais_shape.Attributes().WireAspect().SetTypeOfLine(type_of_line)
        if d.line_width > 0:
            ais_shape.SetWidth(d.line_width)
        return ais_shape

    def create_shape(self):
        pass

    def update_shape(self, change=None):
        d = self.declaration
        edges = TopTools_ListOfShape()
        wires = []
        for c in self.children():
            if not isinstance(c, OccShape):
                continue
            if c.shape is None:
                raise ValueError("Cannot build wire from empty shape: %s" % c)
            self.extract_edges(c, edges)
        else:
            for edge in d.edges:
                if isinstance(edge, TopoDS_Edge):
                    edges.Append(edge)
                else:
                    wires.append(edge)

        builder = BRepBuilderAPI_MakeWire()
        builder.Add(edges)
        for w in wires:
            builder.Add(w)
        if not builder.IsDone():
            log.warning("Edges must be connected %s" % d)
        try:
            wire = builder.Wire()
        except RuntimeError as e:
            msg = f"Error creating wire for {d}: {e}"
            raise RuntimeError(msg)
        if d.reverse:
            wire.Reverse()
        if d.fix:
            fixer = ShapeFix_Wire()
            fixer.Load(wire)
            if fixer.Perform():
                wire = fixer.Wire()

        if surface := d.surface:
            wire = self.apply_to_surface(wire, surface)

        self.curve = BRepAdaptor_CompCurve(wire)
        self.shape = wire

    def apply_to_surface(self, wire: TopoDS_Wire, face: TopoDS_Face) -> TopoDS_Wire:
        # Attempt to put the wire onto the surface given
        finder = BRepBuilderAPI_FindPlane(wire)
        if not finder.Found():
            raise ValueError("Cannot apply a non-planar wire to a surface.")
        plane = BRepBuilderAPI_MakeFace(finder.Plane().Pln()).Face()
        surface = BRepAdaptor_Surface(face).Surface().Surface()
        builder = BRepBuilderAPI_MakeWire()
        for edge in Topology(shape=wire).edges:
            adapter_curve_2d = BRepAdaptor_Curve2d(edge, plane)
            new_edge = BRepBuilderAPI_MakeEdge(
                adapter_curve_2d.Curve(),
                surface,
                adapter_curve_2d.FirstParameter(),
                adapter_curve_2d.LastParameter(),
            ).Edge()
            builder.Add(new_edge)
        return builder.Wire()

    def extract_edges(self, child, edges):
        d = child.declaration
        if isinstance(child.shape, list):
            for c in child.children():
                if not isinstance(c, OccShape):
                    continue
                self.extract_edges(c, edges)
        else:
            for edge in d.topology.edges:
                if getattr(d, "surface", None):
                    BRepLib.BuildCurves3d_(edge)
                edges.Append(edge)

    def get_value_at(self, t, derivative=0):
        if self.curve is None:
            self.update_shape()
        return Topology.get_value_at(self.curve, t, derivative)
