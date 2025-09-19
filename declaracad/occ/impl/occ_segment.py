"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""

from atom.api import Typed
from OCCT.GC import GC_MakeSegment
from OCCT.Geom import Geom_TrimmedCurve

from declaracad.occ.draw import ProxySegment

from .occ_line import OccLine


class OccSegment(OccLine, ProxySegment):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/class_g_c___make_segment.html"
    )

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        points = self.get_transformed_points()
        if len(points) != 2:
            raise ValueError("A segment requires exactly two points")
        segment = self.curve = GC_MakeSegment(points[0], points[1]).Value()
        self.shape = self.make_edge(segment)
