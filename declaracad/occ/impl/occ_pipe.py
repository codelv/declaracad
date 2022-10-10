"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from atom.api import Instance, set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCCT.GeomFill import (
    GeomFill_IsConstantNormal,
    GeomFill_IsCorrectedFrenet,
    GeomFill_IsDarboux,
    GeomFill_IsDiscreteTrihedron,
    GeomFill_IsFixed,
    GeomFill_IsFrenet,
    GeomFill_IsGuideAC,
    GeomFill_IsGuideACWithContact,
    GeomFill_IsGuidePlan,
    GeomFill_IsGuidePlanWithContact,
)
from OCCT.TopoDS import TopoDS_Edge

from declaracad.occ.algo import ProxyPipe

from .occ_algo import OccOperation, coerce_shape
from .occ_shape import OccShape


class OccPipe(OccOperation, ProxyPipe):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___make_pipe.html"
    )

    #: References to observed shapes
    _old_spline = Instance(OccShape)
    _old_profile = Instance(OccShape)

    fill_modes = {
        "corrected_frenet": GeomFill_IsCorrectedFrenet,
        "fixed": GeomFill_IsFixed,
        "frenet": GeomFill_IsFrenet,
        "constant_normal": GeomFill_IsConstantNormal,
        "darboux": GeomFill_IsDarboux,
        "guide_ac": GeomFill_IsGuideAC,
        "guide_plan": GeomFill_IsGuidePlan,
        "guide_ac_contact": GeomFill_IsGuideACWithContact,
        "guide_plan_contact": GeomFill_IsGuidePlanWithContact,
        "discrete_trihedron": GeomFill_IsDiscreteTrihedron,
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

        args = [coerce_shape(spline), coerce_shape(profile)]

        # Make sure spline is a wire
        if isinstance(args[0], TopoDS_Edge):
            args[0] = BRepBuilderAPI_MakeWire(args[0]).Wire()

        if d.fill_mode:
            args.append(self.fill_modes[d.fill_mode])
        pipe = BRepOffsetAPI_MakePipe(*args)
        self.shape = pipe.Shape()

    def set_spline(self, spline):
        self.update_shape()

    def set_profile(self, profile):
        self.update_shape()

    def set_fill_mode(self, mode):
        self.update_shape()
