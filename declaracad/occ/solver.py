"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Atom
from typing import Tuple as TupleType
from declaracad.occ.geom import Point, Direction

from OCCT.gp import gp_Lin2d
from OCCT.GccAna import GccAna_Circ2d3Tan
from OCCT.GccEnt import GccEnt_QualifiedLin, GccEnt_QualifiedCirc


class Solver(Atom):

    @classmethod
    def arc_from_tangent_and_points(
        cls,
        start_tangent: TupleType[Point, Direction],
        end_point: Point,
    ) -> TupleType[float, Point]:
        """ Compute the radius and center point for an arc with the given
        start point and tangent direction to the end point.

        Returns
        -------
        result: Tuple[float, Point]
            A tuple with the radius and center point

        """
        start_point, start_direction = start_tangent
        line = gc_Lin2d(start_point.proxy, start_direction.proxy)
        gca_lin = GccAna_QualifiedLin(line)
        GccAna_Circ2d3Tan(gca_lin, 1e-6)
