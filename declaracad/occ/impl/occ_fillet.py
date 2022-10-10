"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from atom.api import set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCCT.BRepFilletAPI import BRepFilletAPI_MakeFillet, BRepFilletAPI_MakeFillet2d
from OCCT.BRepTools import BRepTools
from OCCT.ChFi3d import ChFi3d_Polynomial, ChFi3d_QuasiAngular, ChFi3d_Rational
from OCCT.gp import gp_Pnt2d
from OCCT.TColgp import TColgp_Array1OfPnt2d
from OCCT.TopoDS import TopoDS_Face, TopoDS_Vertex, TopoDS_Wire

from declaracad.core.utils import log
from declaracad.occ.algo import ProxyFillet

from .occ_algo import OccOperation
from .topology import Topology


class OccFillet(OccOperation, ProxyFillet):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_fillet_a_p_i___make_fillet.html"
    )
    shape_types = {
        "rational": ChFi3d_Rational,
        "angular": ChFi3d_QuasiAngular,
        "polynomial": ChFi3d_Polynomial,
    }

    def update_shape(self, change=None):
        d = self.declaration
        # Get the shape to apply the fillet to
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        s = child.shape
        if isinstance(s, (TopoDS_Wire, TopoDS_Face)):
            self.fillet_2d(child)
        else:
            self.fillet_3d(child)

    def fillet_2d(self, child):
        d = self.declaration
        shape = child.shape
        was_wire = isinstance(shape, TopoDS_Wire)
        if was_wire:
            shape = BRepBuilderAPI_MakeFace(shape).Face()
        builder = BRepFilletAPI_MakeFillet2d(shape)
        operations = d.operations if d.operations else child.topology.vertices
        for item in operations:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                r, v = item
                builder.AddFillet(v, r)
            elif isinstance(item, TopoDS_Vertex):
                builder.AddFillet(item, d.radius)
            else:
                log.warning(f"Invalid fillet {item}")

        shape = Topology.cast_shape(builder.Shape())
        if was_wire:
            shape = BRepTools.OuterWire_(shape)
        self.shape = shape

    def fillet_3d(self, child):
        d = self.declaration
        fillet = BRepFilletAPI_MakeFillet(child.shape)
        operations = d.operations if d.operations else child.topology.edges
        for item in operations:
            if not isinstance(item, (list, tuple)):
                r = d.radius
                if isinstance(item, TopoDS_Face):
                    for edge in Topology(shape=item).edges_from_face(item):
                        fillet.Add(r, edge)
                else:
                    fillet.Add(r, item)
                continue

            # If an array of points is create a changing radius fillet
            n = len(item)
            if n == 2 and isinstance(item[0], (list, tuple)):
                pts, edge = item
                array = TColgp_Array1OfPnt2d(1, len(pts))
                for i, pt in enumerate(pts):
                    array.SetValue(i + 1, gp_Pnt2d(*pt))
                fillet.Add(array, edge)
                continue
            if n == 2 and isinstance(item[1], TopoDS_Face):
                r, face = item
                for edge in Topology(shape=face).edges_from_face(face):
                    fillet.Add(r, edge)
                continue
            # custom radius or r1 and r2 radius fillets
            fillet.Add(*item)
        self.shape = fillet.Shape()

    def set_shape_type(self, shape_type):
        self.update_shape()

    def set_radius(self, r):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()
