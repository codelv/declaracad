"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jan, 15 2022
"""
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve, BRepAdaptor_Curve
from OCCT.GeomLib import GeomLib
from OCCT.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Wire

from declaracad.occ.algo import ProxyExtend

from .occ_algo import OccOperation, coerce_shape


class OccExtend(OccOperation, ProxyExtend):
    def update_shape(self, change=None):
        d = self.declaration
        shape = d.shape
        if shape is None:
            shape = self.get_first_child().shape
        shape = coerce_shape(shape)
        if isinstance(shape, (TopoDS_Edge, TopoDS_Wire)):
            for op in d.operations:
                shape = self.extend_curve(shape, op)
            self.shape = shape
        elif isinstance(shape, TopoDS_Face):
            for op in d.operations:
                shape = self.extend_surface(shape, op)
            self.shape = shape

    def extend_curve(self, shape, op):
        if isinstance(shape, TopoDS_Wire):
            curve = BRepAdaptor_CompCurve(shape)
        else:
            curve = BRepAdaptor_Curve(shape)

        # t = (curve.FirstParameter(), curve.LastParameter())
        # curve.Value(t)
        pnt = op  # TODO: ???
        GeomLib.ExtendCurveToPoint(curve, pnt, 1, True)

    def extend_surface(self, shape, op):
        # surface = Topology.cast_surface(shape)
        raise NotImplementedError("TODO")
