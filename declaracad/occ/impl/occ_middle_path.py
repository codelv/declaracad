"""
Copyright (c) 2021-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Typed, Dict, set_default

from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
)
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MiddlePath
from OCCT.BRepMAT2d import (
    BRepMAT2d_BisectingLocus, BRepMAT2d_Explorer,
    BRepMAT2d_LinkTopoBilo
)
from OCCT.BRep import BRep_Builder, BRep_Tool
from OCCT.BRepLib import BRepLib_MakeEdge
from OCCT.Geom2dAdaptor import Geom2dAdaptor_Curve
from OCCT.MAT import MAT_Arc
from OCCT.TopoDS import TopoDS_Compound, TopoDS_Edge, TopoDS_Face, TopoDS_Wire


from declaracad.occ.draw import ProxyMiddlePath
from .occ_wire import OccWire
from .occ_shape import Shape
from .topology import Topology


class OccMiddlePath(OccWire, ProxyMiddlePath):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___middle_path.html"
    )

    bilo = Typed(BRepMAT2d_BisectingLocus)
    link = Typed(BRepMAT2d_LinkTopoBilo)
    graph = Dict(TopoDS_Edge, MAT_Arc)

    def update_shape(self, change=None):
        d = self.declaration
        n = len(d.shapes)
        if n in (1, 3):
            args = d.shapes
        elif n == 2:
            child = self.get_first_child()
            args = [child.shape] + d.shapes
        else:
            args = [c.shape for c in self.children()]

        for i, s in enumerate(args):
            if isinstance(s, Shape):
                args[i] = s.proxy.shape

        first_shape = Topology.cast_shape(args[0])
        if isinstance(first_shape, (TopoDS_Wire, TopoDS_Face)):
            self.middle_path_2d(first_shape)
        else:
            self.middle_path_3d(args)

    def middle_path_3d(self, args):
        for i, s in enumerate(args[:]):
            if isinstance(s, TopoDS_Edge):
                args[i] = BRepBuilderAPI_MakeWire(s).Wire()
        builder = BRepOffsetAPI_MiddlePath(*args)
        shape = Topology.cast_shape(builder.Shape())
        curve = self.curve = BRepAdaptor_CompCurve(shape)
        self.shape = shape

    def middle_path_2d(self, shape):
        if isinstance(shape, TopoDS_Wire):
            face = BRepBuilderAPI_MakeFace(shape).Face()
        else:
            face = shape
        explorer = BRepMAT2d_Explorer(face)
        bilo = self.bilo = BRepMAT2d_BisectingLocus()
        bilo.Compute(explorer)
        if not bilo.IsDone():
            raise RuntimeError(f"Could not build path {d}")
        link = self.link = BRepMAT2d_LinkTopoBilo()
        link.Perform(explorer, bilo)
        graph = bilo.Graph()
        surf = BRep_Tool.Surface_(face)
        for j in range(1, graph.NumberOfArcs() + 1):
            arc = graph.Arc(j)
            bisector = bilo.GeomBis(arc, False)[0]
            curve = Geom2dAdaptor_Curve(bisector.Value())
            t = curve.FirstParameter(), curve.LastParameter()
            e = BRepLib_MakeEdge(curve.Curve(), surf, *t).Edge()
            self.graph[e] = arc

        wires = Topology.join_edges(self.graph.keys())
        if len(wires) == 1:
            self.curve = BRepAdaptor_CompCurve(wires[0])
        else:
            builder = BRep_Builder()
            shape = TopoDS_Compound()
            builder.MakeCompound(shape)
            for w in wires:
                builder.Add(shape, w)
        self.shape = shape

    def set_shapes(self, shapes):
        self.update_shape()
