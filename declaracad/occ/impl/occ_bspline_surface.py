"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 24, 2021

@author: jrm
"""

from atom.api import Typed
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCCT.Geom import Geom_BSplineSurface
from OCCT.GeomAPI import GeomAPI_PointsToBSplineSurface
from OCCT.TColgp import TColgp_Array2OfPnt

from declaracad.occ.draw import ProxyBSplineSurface
from declaracad.occ.geom import Point

from .occ_bspline import CONTINUITY
from .occ_shape import OccShape


class OccBSplineSurface(OccShape, ProxyBSplineSurface):
    reference = (  # type: ignore
        "https://dev.opencascade.org/doc/refman/html/"
        "class_geom_a_p_i___points_to_b_spline_surface.html"
    )

    surface = Typed(Geom_BSplineSurface)

    def create_points(self, grid: list[list[Point]]):
        nrows = len(grid)
        ncols = len(grid[0])
        points = TColgp_Array2OfPnt(1, nrows, 1, ncols)
        set_value = points.SetValue
        i = 0
        for row in grid:
            i += 1
            j = 0
            for pnt in row:
                j += 1
                set_value(i, j, pnt.proxy)
        return points

    def create_shape(self):
        d = self.declaration
        points = self.create_points(d.points)
        if d.interpolate:
            f = GeomAPI_PointsToBSplineSurface()
            f.Interpolate(points, d.periodic)
        else:
            cty = CONTINUITY[d.continuity]
            f = GeomAPI_PointsToBSplineSurface(
                points, d.deg_min, d.deg_max, cty, d.tolerance
            )
        surface = self.surface = f.Surface()
        builder = BRepBuilderAPI_MakeFace(surface, d.tolerance)
        self.shape = builder.Face()

    def set_shapes(self, shapes):
        self.update_shape()
