"""
Copyright (c) 2021-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from typing import Any, Optional

from atom.api import Dict, Typed, set_default
from OCCT.BRep import BRep_Builder, BRep_Tool
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
)
from OCCT.BRepMAT2d import (
    BRepMAT2d_BisectingLocus,
    BRepMAT2d_Explorer,
    BRepMAT2d_LinkTopoBilo,
)
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MiddlePath
from OCCT.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection, GeomAbs_Tangent
from OCCT.MAT import MAT_Arc, MAT_Left
from OCCT.TopoDS import (
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Wire,
)

from declaracad.occ.draw import ProxyMiddlePath

from .occ_shape import Shape
from .occ_wire import OccWire
from .topology import Topology


class OccMiddlePath(OccWire, ProxyMiddlePath):
    reference = set_default(  # type: ignore
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___middle_path.html"
    )

    # ------------------------------------------------------------------------
    # 2D Parameters
    # ------------------------------------------------------------------------
    bilo = Typed(BRepMAT2d_BisectingLocus)
    link = Typed(BRepMAT2d_LinkTopoBilo)
    explorer = Typed(BRepMAT2d_Explorer)
    graph = Dict(TopoDS_Edge, MAT_Arc)
    face = Typed(TopoDS_Face)

    join_types = {
        "arc": GeomAbs_Arc,
        "tangent": GeomAbs_Tangent,
        "intersection": GeomAbs_Intersection,
    }

    def update_shape(self, change: Optional[dict[str, Any]] = None):
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

    def middle_path_3d(self, args: list):
        for i, s in enumerate(args[:]):
            if isinstance(s, TopoDS_Edge):
                args[i] = BRepBuilderAPI_MakeWire(s).Wire()
        builder = BRepOffsetAPI_MiddlePath(*args)
        shape = Topology.cast_shape(builder.Shape())
        self.curve = BRepAdaptor_CompCurve(shape)
        self.shape = shape

    def middle_path_2d(self, shape: TopoDS_Shape):
        d = self.declaration
        if isinstance(shape, TopoDS_Wire):
            face = BRepBuilderAPI_MakeFace(shape).Face()
        else:
            face = shape
        self.face = face
        explorer = self.explorer = BRepMAT2d_Explorer(face)
        bilo = self.bilo = BRepMAT2d_BisectingLocus()

        is_open = False

        join_type = self.join_types[d.join_type]
        line_index = 1
        side = MAT_Left
        bilo.Compute(explorer, line_index, side, join_type, is_open)
        if not bilo.IsDone():
            raise RuntimeError(f"Could not build middle path {d}")
        link = self.link = BRepMAT2d_LinkTopoBilo()
        link.Perform(explorer, bilo)
        graph = bilo.Graph()
        surf = BRep_Tool.Surface_(face)

        touching = d.mode in ("normal", "no-trim")
        tol = d.tolerance
        for j in range(1, graph.NumberOfArcs() + 1):
            arc = graph.Arc(j)
            if not touching:
                if arc.FirstNode().Distance() < tol:
                    continue
                if arc.SecondNode().Distance() < tol:
                    continue
            bisector, rev = bilo.GeomBis(arc, False)
            curve = bisector.Value()

            # Use the basis curve or the type information is lost
            t1, t2 = curve.FirstParameter(), curve.LastParameter()
            n1, n2 = arc.FirstNode(), arc.SecondNode()
            if n1.Infinite() or n2.Infinite():
                edge = BRepBuilderAPI_MakeEdge(curve, surf).Edge()
            else:
                edge = BRepBuilderAPI_MakeEdge(curve, surf, t1, t2).Edge()
            self.graph[edge] = arc

        builder = BRep_Builder()
        shape = TopoDS_Compound()
        builder.MakeCompound(shape)
        for e in self.graph.keys():
            builder.Add(shape, e)

        # Create 3d curves
        # BRepLib.BuildCurves3d_(shape)

        self.shape = shape

    def set_shapes(self, shapes: list[Shape]):
        self.update_shape()

    def set_mode(self, mode: str):
        self.update_shape()

    def set_join_type(self, join_type: str):
        self.update_shape()
