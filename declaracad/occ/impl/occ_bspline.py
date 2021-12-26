"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 24, 2021

@author: jrm
"""
from atom.api import Typed, set_default

from OCCT.Geom import Geom_BSplineCurve
from OCCT.GeomAbs import GeomAbs_C0, GeomAbs_C1, GeomAbs_C2, GeomAbs_C3, GeomAbs_CN
from OCCT.GeomAPI import GeomAPI_Interpolate, GeomAPI_PointsToBSpline
from OCCT.TColgp import TColgp_Array1OfPnt, TColgp_HArray1OfPnt, TColgp_Array1OfVec
from OCCT.TColStd import (
    TColStd_HArray1OfBoolean,
    TColStd_Array1OfReal,
    TColStd_HArray1OfReal,
)

from declaracad.occ.draw import ProxyBSpline
from .occ_line import OccLine


CONTINUITY = {
    0: GeomAbs_C0,
    1: GeomAbs_C1,
    2: GeomAbs_C2,
    3: GeomAbs_C3,
    None: GeomAbs_CN,
}


class OccBSpline(OccLine, ProxyBSpline):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_geom___b_spline_curve.html"
    )

    curve = Typed(Geom_BSplineCurve)

    def create_shape(self):
        d = self.declaration
        if not d.points:
            raise ValueError("Must have at least two points")

        # Poles and weights
        points = self.get_transformed_points()

        if d.interpolate or d.tangents or d.periodic:
            pts = TColgp_HArray1OfPnt(1, len(points))
            for i, p in enumerate(points):
                pts.SetValue(i + 1, p)

            if d.parameters:
                params = TColStd_HArray1OfReal(1, len(points))
                for i, p in enumerate(d.parameters):
                    params.SetValue(i + 1, p)
                f = GeomAPI_Interpolate(pts, params, d.periodic, d.tolerance)
            else:
                f = GeomAPI_Interpolate(pts, d.periodic, d.tolerance)

            if d.tangents:
                n = len(d.tangents)
                if n == 2:
                    start, end = d.tangents
                    f.Load(gp_Vec(*start), gp_Vec(*end))
                else:
                    tangents = TColgp_Array1OfVec(1, n)
                    flags = TColStd_HArray1OfBoolean(1, n)
                    for i, p in enumerate(d.parameters):
                        tangents.SetValue(i + 1, p)
                        flags.SetValue(i + 1, True)
                    f.Load(tangents, flags)

            f.Perform()
        else:
            cty = CONTINUITY[d.continuity]
            pts = TColgp_Array1OfPnt(1, len(points))
            for i, p in enumerate(points):
                pts.SetValue(i + 1, p)

            if d.parameters:
                params = TColStd_Array1OfReal(1, len(points))
                for i, p in enumerate(d.parameters):
                    params.SetValue(i + 1, p)
                f = GeomAPI_PointsToBSpline(
                    pts, params, d.deg_min, d.deg_max, cty, d.tolerance
                )
            else:
                f = GeomAPI_PointsToBSpline(pts, d.deg_min, d.deg_max, cty, d.tolerance)
        curve = self.curve = f.Curve()
        self.shape = self.make_edge(curve)
