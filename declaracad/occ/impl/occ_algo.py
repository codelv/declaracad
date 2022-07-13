"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import Dict, Instance, Int, Subclass, set_default
from OCCT.BRep import BRep_Builder
from OCCT.BRepAlgoAPI import (
    BRepAlgoAPI_BooleanOperation,
    BRepAlgoAPI_Common,
    BRepAlgoAPI_Cut,
    BRepAlgoAPI_Fuse,
)
from OCCT.BRepBuilderAPI import BRepBuilderAPI_Sewing
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCCT.TopoDS import (
    TopoDS,
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shape,
    TopoDS_Vertex,
    TopoDS_Wire,
)
from OCCT.TopTools import TopTools_ListOfShape

from declaracad.core.utils import log
from declaracad.occ.algo import (
    ProxyBooleanOperation,
    ProxyCommon,
    ProxyCut,
    ProxyFuse,
    ProxyGlue,
    ProxyOperation,
    ProxySew,
)

from .occ_shape import OccDependentShape, OccShape, Topology, coerce_axis, coerce_shape


class OccOperation(OccDependentShape, ProxyOperation):
    """Operation is a dependent shape that uses queuing to only
    perform the operation once all changes have settled because
    in general these operations are expensive.
    """

    pass


class OccBooleanOperation(OccOperation, ProxyBooleanOperation):
    """Base class for a boolean shape operation."""

    op = Subclass(BRepAlgoAPI_BooleanOperation)

    def update_shape(self, change=None):
        op = self.op()
        d = self.declaration

        shapes = []
        unify = d.unify
        if d.shape1 and d.shape2:
            shapes = [coerce_shape(d.shape1), coerce_shape(d.shape2)]
        else:
            shapes = []
        shapes.extend(list(self.child_shapes()))

        shape, *other_shapes = shapes

        if d.disabled:
            self.shape = Topology.cast_shape(shape)
            return

        if d.parallel and other_shapes:
            builder = self.op()
            builder.SetFuzzyValue(d.tolerance)
            shape_list = TopTools_ListOfShape()
            shape_list.Append(shape)

            tool_list = TopTools_ListOfShape()
            for s in other_shapes:
                tool_list.Append(s)

            builder.SetArguments(shape_list)
            builder.SetTools(tool_list)
            builder.SetRunParallel(True)
            builder.Build()
            builder.Check()
            if unify:
                builder.SimplifyResult()

            shape = builder.Shape()
        else:
            for other_shape in other_shapes:
                builder = self.op(shape, other_shape)
                if unify:
                    builder.SimplifyResult()
                shape = builder.Shape()

        if d.fix:
            fixer = ShapeFix_Shape(shape)
            if fixer.Perform():
                shape = fixer.Shape()

        self.shape = Topology.cast_shape(shape)

    def set_parallel(self, parallel):
        self.update_shape()

    def set_disabled(self, disabled):
        self.update_shape()

class OccCommon(OccBooleanOperation, ProxyCommon):
    """Common of all the child shapes together."""

    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_algo_a_p_i___common.html"
    )
    op = set_default(BRepAlgoAPI_Common)


class OccCut(OccBooleanOperation, ProxyCut):
    """Cut all the child shapes from the first shape."""

    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_algo_a_p_i___cut.html"
    )
    op = set_default(BRepAlgoAPI_Cut)


class OccFuse(OccBooleanOperation, ProxyFuse):
    """Fuse all the child shapes together."""

    reference = set_default(
        "https://dev.opencascade.org/doc/overview/html/"
        "occt_user_guides__boolean_operations.html#occt_algorithms_7"
    )
    op = set_default(BRepAlgoAPI_Fuse)


class OccSew(OccOperation, ProxySew):
    def update_shape(self, change=None):
        d = self.declaration
        builder = BRepBuilderAPI_Sewing()
        for s in self.child_shapes():
            builder.Add(Topology.cast_shape(s))
        builder.Perform()
        self.shape = Topology.cast_shape(builder.SewedShape())


class OccGlue(OccOperation, ProxyGlue):
    def update_shape(self, change=None):
        d = self.declaration
        raise NotImplementedError  # TODO: This
