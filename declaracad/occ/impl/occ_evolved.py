"""
Copyright (c) 2025, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MakeEvolved
from OCCT.GeomAbs import GeomAbs_Arc, GeomAbs_Intersection, GeomAbs_Tangent
from OCCT.TopoDS import TopoDS_Edge

from declaracad.occ.algo import ProxyEvolved

from .occ_algo import OccOperation, coerce_shape


class OccEvolved(OccOperation, ProxyEvolved):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___make_evolved.html"
    )

    join_types = {
        "arc": GeomAbs_Arc,
        "tangent": GeomAbs_Tangent,
        "intersection": GeomAbs_Intersection,
    }

    def update_shape(self, change=None):
        d = self.declaration

        if d.spline and d.profile:
            spline, profile = d.spline, d.profile
        elif d.spline:
            spline = d.spline
            profile = self.get_first_child().shape
        elif d.profile:
            profile = d.profile
            spline = self.get_first_child().shape
        else:
            shapes = list(self.child_shapes())
            spline, profile = shapes[0:2]

        args = [
            coerce_shape(spline),
            coerce_shape(profile),
            self.join_types[d.join_type],
            d.global_axis,
            d.solid,
            d.require_profile_on_spline,
            d.tolerance,
            d.volume,
            d.parallel,
        ]

        # Make sure spline is a wire
        for i, arg in enumerate(args[0:2]):
            if isinstance(arg, TopoDS_Edge):
                args[i] = BRepBuilderAPI_MakeWire(arg).Wire()

        evolved = BRepOffsetAPI_MakeEvolved(*args)
        self.shape = evolved.Shape()

    def set_spline(self, spline):
        self.update_shape()

    def set_profile(self, profile):
        self.update_shape()
