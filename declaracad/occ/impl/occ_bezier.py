"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import Typed
from OCCT.Geom import Geom_BezierCurve
from OCCT.TColgp import TColgp_Array1OfPnt

from declaracad.occ.draw import ProxyBezier

from .occ_line import OccLine


class OccBezier(OccLine, ProxyBezier):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/class_geom___bezier_curve.html"
    )

    curve = Typed(Geom_BezierCurve)

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        if n < 2:
            raise ValueError("A bezier must have at least 2 points!")

        points = self.get_transformed_points()
        pts = TColgp_Array1OfPnt(1, n)
        set_value = pts.SetValue

        # TODO: Support weights
        for i, p in enumerate(points):
            set_value(i + 1, p)

        curve = self.curve = Geom_BezierCurve(pts)
        self.shape = self.make_edge(curve)
