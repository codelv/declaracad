"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jan 27, 2022
"""
from atom.api import Typed, set_default
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
)
from OCCT.GccAna import GccAna_Lin2d2Tan
from OCCT.GccEnt import GccEnt
from OCCT.gce import gce_MakePln
from OCCT.Geom import Geom_Circle
from OCCT.Geom2d import Geom2d_Circle, Geom2d_Line, Geom2d_TrimmedCurve
from OCCT.GeomAPI import GeomAPI
from OCCT.gp import gp_Pln, gp_Ax2, gp_Circ, gp_Pnt2d

from declaracad.occ.draw import ProxyCircuit

from typing import Optional

from .occ_wire import OccWire
from .topology import Topology


class OccCircuit(OccWire, ProxyCircuit):
    curve = Typed(BRepAdaptor_CompCurve)

    def calculate_parameters(
        self, circles: list, pln: gp_Pln, clockwise: bool, offset: float
    ):
        normal = pln.Position().Direction()

        enclosing = GccEnt.Enclosing_
        outside = GccEnt.Outside_
        if clockwise:
            enclosing, outside = outside, enclosing

        for circle in circles:
            axis = gp_Ax2(circle.position.proxy, normal)
            if offset < 0:
                dr = offset if circle.radius < 0 else 0
            else:
                dr = 0 if circle.radius < 0 else offset
            r = abs(circle.radius + dr)
            geom_circle = Geom_Circle(gp_Circ(axis, r))
            c = GeomAPI.To2d_(geom_circle, pln).Circ2d()
            reverse = circle.radius < 0

            if reverse:
                if circle.reverse:
                    param = outside(c)
                else:
                    param = enclosing(c)
            else:
                if circle.reverse:
                    param = enclosing(c)
                else:
                    param = outside(c)
            yield (param, geom_circle, reverse)

    def create_shape(self):
        d = self.declaration
        circles = d.circles[:]

        n = len(circles)
        if n < 2:
            raise ValueError("At least 2 circles are required")

        # Determine direction
        if n > 2:
            polygon = BRepBuilderAPI_MakePolygon()
            for circle in circles:
                polygon.Add(circle.position.proxy)
            clockwise = Topology.is_clockwise(polygon.Wire())

            # Normal plane
            builder = gce_MakePln(*(c.position.proxy for c in circles[0:3]))
        else:
            c = circles[0]
            builder = gce_MakePln(c.position.proxy, c.direction.proxy)
            clockwise = True

        if not builder.IsDone():
            raise ValueError(f"Could not build {d}: Circles must be on the same plane")
        pln = builder.Value()

        if d.reverse:
            clockwise = not clockwise

        tol = d.tolerance
        shape = BRepBuilderAPI_MakeWire()
        edges = []

        #: List of parameters
        parameters = list(self.calculate_parameters(circles, pln, clockwise, d.offset))

        # Solution of last intersection
        a0: Optional[float] = None

        # Solution of first arc intersection
        afirst: Optional[float] = None

        n = len(parameters)
        for i in range(n):
            a, geom_circle, reverse = parameters[i]
            b, next_circle, next_reverse = parameters[(i + 1) % n]
            r = GccAna_Lin2d2Tan(a, b, tol)
            if not r.IsDone():
                raise ValueError(f"Could not solve {d}")

            p1, p2 = gp_Pnt2d(), gp_Pnt2d()
            t1, a1 = r.Tangency1(1, 0, 0, p1)
            t2, a2 = r.Tangency2(1, 0, 0, p2)

            if a0 is not None:
                if reverse:
                    a0, a1 = a1, a0
                edge = BRepBuilderAPI_MakeEdge(geom_circle, a0, a1).Edge()
                shape.Add(edge)
            else:
                afirst = a1

            # Add line
            line = Geom2d_Line(r.ThisSolution(1))
            geom_line = GeomAPI.To3d_(line, pln)
            edge = BRepBuilderAPI_MakeEdge(geom_line, t1, t2).Edge()
            shape.Add(edge)
            a0 = a2

        # Add first with initial solution
        if next_reverse:
            a2, afirst = afirst, a2
        edge = BRepBuilderAPI_MakeEdge(next_circle, a2, afirst).Edge()
        shape.Add(edge)

        wire = shape.Wire()
        curve = self.curve = BRepAdaptor_CompCurve(wire)
        self.shape = wire

    def init_layout(self):
        # This does not depened on children
        pass

    def update_shape(self, change=None):
        self.create_shape()
