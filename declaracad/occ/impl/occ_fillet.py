"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""

from OCCT.BRepAlgoAPI import BRepAlgoAPI_Common
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
)
from OCCT.BRepFilletAPI import BRepFilletAPI_MakeFillet, BRepFilletAPI_MakeFillet2d
from OCCT.BRepTools import BRepTools
from OCCT.ChFi3d import ChFi3d_Polynomial, ChFi3d_QuasiAngular, ChFi3d_Rational
from OCCT.gp import gp_Pnt2d
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.TColgp import TColgp_Array1OfPnt2d
from OCCT.TopoDS import (
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCCT.TopTools import TopTools_ListOfShape

from declaracad.core.utils import log
from declaracad.occ.algo import ProxyFillet

from .occ_algo import OccOperation
from .occ_polyline import OccPolyline
from .topology import Point, Topology


class OccFillet(OccOperation, ProxyFillet):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_fillet_a_p_i___make_fillet.html"
    )
    shape_types = {
        "rational": ChFi3d_Rational,
        "angular": ChFi3d_QuasiAngular,
        "polynomial": ChFi3d_Polynomial,
    }

    def update_shape(self, change=None):
        d = self.declaration
        # Get the shape to apply the fillet to
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        s = child.shape
        if isinstance(child, OccPolyline):
            shape = self.fillet_polyline(child)
        elif isinstance(s, (TopoDS_Wire, TopoDS_Face)):
            shape = self.fillet_2d(child)
        else:
            shape = self.fillet_3d(child)

        if d.fix:
            fixer = ShapeFix_Shape(shape)
            if fixer.Perform():
                shape = fixer.Shape()
        self.shape = shape

    def fillet_polyline(self, child: OccPolyline) -> TopoDS_Shape:
        """Fillet a polyline that may be 3d"""
        d = self.declaration
        points = child.declaration.points
        operations = d.operations if d.operations else child.topology.vertices
        wires = []

        # Fillet each segment of the wire
        for i in range(1, len(points) - 1):
            p0 = points[i - 1]
            p1 = points[i]
            p2 = points[i + 1]

            radius = None

            # Create a polyline
            poly = BRepBuilderAPI_MakePolygon()
            poly.Add(p0.proxy)
            poly.Add(p1.proxy)
            poly.Add(p2.proxy)
            wire = Topology.cast_shape(poly.Shape())
            middle_vertex = Topology(shape=wire).vertices[1]

            # Determine if the vertex was filleted
            point = Point(middle_vertex)
            for item in operations:
                if isinstance(item, (tuple, list)):
                    r, v = item
                    if point == v:
                        radius = r
                        break
                elif isinstance(item, TopoDS_Vertex):
                    if point == item:
                        radius = d.radius
                        break
                else:
                    log.warning(f"Invalid fillet {item}")

            if radius is not None:
                face = BRepBuilderAPI_MakeFace(wire).Face()
                fillet = BRepFilletAPI_MakeFillet2d(face)
                fillet.AddFillet(middle_vertex, radius)
                result = Topology.cast_shape(fillet.Shape())
                wire = BRepTools.OuterWire_(result)
            wires.append(wire)

        assert wires
        if len(wires) == 1:
            return wires[0]  # No merging needed

        # Merge filleted edges by taking the intersection of overlapping segments
        edges = []
        last_index = len(wires) - 1
        for i in range(1, len(wires)):
            last_wire = wires[i - 1]
            wire = wires[i]
            last_topo = Topology(shape=last_wire)
            topo = Topology(shape=wire)
            if last_topo.end_point == topo.start_point:
                # No fillet
                edges.extend(last_topo.edges)
            else:
                if i == 1:
                    # Add starting edges
                    edges.extend(last_topo.edges[0:-1])
                common = BRepAlgoAPI_Common(last_wire, wire)
                common.Build()
                common_edges = Topology(shape=common.Shape()).edges
                assert common_edges, "Fillet radius too large"
                edges.extend(common_edges)
                edges.append(topo.edges[1])  # Add filleted edge
                if i == last_index and len(topo.edges) > 2:
                    # Add final edge
                    edges.extend(topo.edges[2:])

        # Create a wire
        shapes = TopTools_ListOfShape()
        for edge in edges:
            shapes.Append(edge)
        builder = BRepBuilderAPI_MakeWire()
        builder.Add(shapes)
        assert builder.IsDone(), f"Could not create wire with filleted edges {d}"
        return builder.Wire()

    def fillet_2d(self, child) -> TopoDS_Shape:
        d = self.declaration
        shape = child.shape
        was_wire = isinstance(shape, TopoDS_Wire)
        if was_wire:
            shape = BRepBuilderAPI_MakeFace(shape).Face()
        builder = BRepFilletAPI_MakeFillet2d(shape)
        operations = d.operations if d.operations else child.topology.vertices
        for item in operations:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                r, v = item
                builder.AddFillet(v, r)
            elif isinstance(item, TopoDS_Vertex):
                builder.AddFillet(item, d.radius)
            else:
                log.warning(f"Invalid fillet {item}")

        shape = Topology.cast_shape(builder.Shape())
        if was_wire:
            shape = BRepTools.OuterWire_(shape)
        return shape

    def fillet_3d(self, child) -> TopoDS_Shape:
        d = self.declaration
        fillet = BRepFilletAPI_MakeFillet(child.shape)
        operations = d.operations if d.operations else child.topology.edges
        for item in operations:
            if not isinstance(item, (list, tuple)):
                r = d.radius
                if isinstance(item, TopoDS_Face):
                    for edge in Topology(shape=item).edges_from_face(item):
                        fillet.Add(r, edge)
                elif isinstance(item, TopoDS_Wire):
                    for edge in Topology(shape=item).edges_from_wire(item):
                        fillet.Add(r, edge)
                else:
                    fillet.Add(r, item)
                continue

            # If an array of points is create a changing radius fillet
            n = len(item)
            if n == 2 and isinstance(item[0], (list, tuple)):
                pts, edge = item
                array = TColgp_Array1OfPnt2d(1, len(pts))
                for i, pt in enumerate(pts):
                    array.SetValue(i + 1, gp_Pnt2d(*pt))
                fillet.Add(array, edge)
                continue
            if n == 2:
                if isinstance(item[1], TopoDS_Face):
                    r, face = item
                    for edge in Topology(shape=face).edges_from_face(face):
                        fillet.Add(r, edge)
                    continue
                elif isinstance(item[1], TopoDS_Wire):
                    r, wire = item
                    for edge in Topology(shape=wire).edges_from_wire(wire):
                        fillet.Add(r, edge)
                    continue
            # custom radius or r1 and r2 radius fillets
            fillet.Add(*item)
        return fillet.Shape()

    def set_shape_type(self, shape_type):
        self.update_shape()

    def set_radius(self, r):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()
