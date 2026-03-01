"""
Copyright (c) 2025, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_Transform,
)
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeCylinder, BRepPrimAPI_MakeRevol
from OCCT.gp import gp_Pnt

from declaracad.occ.shape import ProxyHole

from .occ_shape import AZ, OccShape, coerce_axis


class OccHole(OccShape, ProxyHole):
    reference = ""

    def create_shape(self):
        d = self.declaration
        r = d.diameter / 2
        h = d.depth
        if d.far_edge.distance or d.near_edge.distance:
            poly = BRepBuilderAPI_MakePolygon()

            poly.Add(gp_Pnt(0, 0, 0))
            if edge_style := d.near_edge:
                d1 = abs(edge_style.distance)
                d2 = abs(edge_style.distance2 or d1)
                if edge_style.kind == "chamfer":
                    d1 = -d1
                y = r + d1
                if y < 0:
                    raise ValueError(
                        f"Near edge chamfer distance cannot be > hole radius. Got  R={r} D={d1}"
                    )
                elif y > 0:
                    poly.Add(gp_Pnt(0, y, 0))
                # If y == 0 skip the point
                poly.Add(gp_Pnt(0, r, d2))
            else:
                poly.Add(gp_Pnt(0, r, 0))

            if edge_style := d.far_edge:
                d1 = abs(edge_style.distance)
                d2 = abs(edge_style.distance2 or d1)
                if edge_style.kind == "chamfer":
                    d1 = -d1
                poly.Add(gp_Pnt(0, r, h - d2))
                y = r + d1
                if y < 0:
                    raise ValueError(
                        f"Far edge chamfer cannot be > hole radius. Got R={r} D={d1}"
                    )
                elif y > 0:
                    poly.Add(gp_Pnt(0, y, h))
                # If y == 0 skip the point
            else:
                poly.Add(gp_Pnt(0, r, h))
            poly.Add(gp_Pnt(0, 0, h))
            poly.Close()
            face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
            revol = BRepPrimAPI_MakeRevol(face, AZ, False)
            t = self.get_transform()
            shape = BRepBuilderAPI_Transform(revol.Shape(), t, False).Shape()
        else:
            cylinder = BRepPrimAPI_MakeCylinder(coerce_axis(d.axis), r, h)
            shape = cylinder.Shape()

        self.shape = shape

    def set_diameter(self, diameter: float):
        self.create_shape()

    def set_depth(self, depth: float):
        self.create_shape()

    def set_top_edge(self, value):
        self.create_shape()

    def set_bottom_edge(self, value):
        self.create_shape()
