"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from math import pi

from atom.api import Typed, set_default
from OCCT.GC import GC_MakeArcOfCircle
from OCCT.Geom import Geom_TrimmedCurve
from OCCT.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Vec

from declaracad.occ.draw import ProxyArc
from declaracad.occ.geom import Direction

from .occ_line import OccLine


class OccArc(OccLine, ProxyArc):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_g_c___make_arc_of_circle.html"
    )

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        try:
            case = 0
            if d.solve:
                arc = self.create_arc_from_solver(**d.solve)
                case = 1
            elif d.radius:
                points = [p.proxy for p in d.points]  # Do not trasnform these
                # if d.radius2:
                #    g = gp_Elips(coerce_axis(d.axis), d.radius, d.radius2)
                #    factory = GC_MakeArcOfEllipse
                # else:
                v = d.direction.proxy
                # TODO: This technially isn't correct because the z axis could
                # already be flipped
                if d.clockwise:
                    v = v.Reversed()
                axis = gp_Ax2(d.position.proxy, v)
                c = gp_Circ(axis, d.radius)

                if n == 2:
                    start, end = points
                    if start.IsEqual(end, d.tolerance):
                        case = 2
                        # Full circle
                        center = d.position.proxy
                        start_direction = gp_Dir(gp_Vec(center, start))
                        start_angle = axis.XDirection().Angle(start_direction)
                        angle = start_angle + 2 * pi
                        arc = GC_MakeArcOfCircle(c, start, angle, True).Value()
                    else:
                        case = 3
                        arc = GC_MakeArcOfCircle(c, start, end, True).Value()
                elif n == 1:
                    case = 4
                    arc = GC_MakeArcOfCircle(c, points[0], d.alpha1, True).Value()
                else:
                    case = 5
                    arc = GC_MakeArcOfCircle(c, d.alpha1, d.alpha2, True).Value()
            # elif n == 2:
            #    # TODO: This doesn't work
            #    points = self.get_transformed_points()
            #    arc = GC_MakeArcOfEllipse(points[0], points[1]).Value()
            elif n == 3:
                if isinstance(d.points[1], Direction):
                    points = self.get_transformed_points([d.points[0], d.points[2]])
                    points.insert(1, gp_Vec(d.points[1].proxy))
                else:
                    points = self.get_transformed_points()
                case = 6
                arc = GC_MakeArcOfCircle(points[0], points[1], points[2]).Value()
            else:
                raise ValueError(
                    "Could not create an Arc with the given children "
                    "and parameters. Must be given one of:\n\t"
                    "- two or three points\n\t"
                    "- radius and 2 points\n\t"
                    "- radius, alpha1 and one point\n\t"
                    "- radius, alpha1 and alpha2\n\t"
                    f"got radius={d.radius} points={d.points} (n={n})"
                )
        except RuntimeError as e:
            help_msg = ""
            if d.points:
                help_msg = "Are points and position on a single plane?"
            raise RuntimeError(
                f"Could not create arc {d}: {e} "
                f"(center={d.position}, radius={d.radius}, points={d.points},"
                f" alpha1={d.alpha1}, alpha2={d.alpha2} case={case})"
                + help_msg
            )

        if d.reverse:
            arc.Reverse()
        self.curve = arc
        self.shape = self.make_edge(arc)

    def create_arc_from_solver(self, **params):
        """Create an arc by solving the given parameters."""
        raise NotImplementedError("TODO")

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_alpha1(self, a):
        self.create_shape()

    def set_alpha2(self, a):
        self.create_shape()

    def set_reverse(self, reverse):
        self.create_shape()

    def set_clockwise(self, clockwise):
        self.create_shape()
