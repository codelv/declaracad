"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from atom.api import Dict, set_default
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeFace
from OCCT.BRepFilletAPI import (BRepFilletAPI_MakeChamfer,
                                BRepFilletAPI_MakeFillet,
                                BRepFilletAPI_MakeFillet2d)
from OCCT.BRepTools import BRepTools
from OCCT.gp import gp_Pnt2d
from OCCT.TColgp import TColgp_Array1OfPnt2d
from OCCT.TopoDS import TopoDS_Edge, TopoDS_Face, TopoDS_Wire

from declaracad.core.utils import log
from declaracad.occ.algo import ProxyChamfer

from .occ_algo import OccOperation
from .topology import Topology


class OccChamfer(OccOperation, ProxyChamfer):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_fillet_a_p_i___make_chamfer.html"
    )
    context = Dict()

    def update_shape(self, change=None):
        d = self.declaration

        #: Get the shape to apply the fillet to
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return
        if isinstance(child.shape, (TopoDS_Wire, TopoDS_Face)):
            self.chamfer_2d(child)
        elif self.has_profile_operations():
            self.chamfer_profile(child)
        else:
            self.chamfer_3d(child)

    def has_profile_operations(self) -> bool:
        T = (tuple, list)
        for item in self.declaration.operations:
            if isinstance(item, T) and isinstance(item[0], T):
                return True
        return False

    def chamfer_2d(self, child):
        d = self.declaration
        shape = child.shape
        was_wire = isinstance(shape, TopoDS_Wire)
        if was_wire:
            shape = BRepBuilderAPI_MakeFace(shape).Face()
        builder = BRepFilletAPI_MakeFillet2d(shape)
        operations = d.operations if d.operations else child.topology.vertices

        for item in operations:
            d1, d2 = d.distance, d.distance2 or d.distance
            if isinstance(item, (tuple, list)):
                n = len(item)
                if n == 2:
                    e1, e2 = item
                    builder.AddChamfer(e1, e2, d1, d2)
                elif n == 3:
                    d1, e1, e2 = item
                    builder.AddChamfer(e1, e2, d1, d1)
                elif n == 4:
                    d1, d2, e1, e2 = item
                    builder.AddChamfer(e1, e2, d1, d2)
                else:
                    log.warning(f"Invalid chamfer {item}")
            else:
                log.warning(f"Invalid chamfer {item}")

        shape = Topology.cast_shape(builder.Shape())
        if was_wire:
            shape = BRepTools.OuterWire_(shape)
        self.shape = shape

    def chamfer_3d(self, child):
        d = self.declaration
        shape = child.shape
        operations = d.operations if d.operations else child.topology.faces

        if self.has_profile_operations():
            self.shape = self.chamfer_profile(shape, d.operations)
            return

        chamfer = BRepFilletAPI_MakeChamfer(shape)
        for item in operations:
            edge = None
            d1, d2 = d.distance, d.distance2 or d.distance
            if isinstance(item, (tuple, list)):
                face = item[-1]
                n = len(item)
                if n > 1:
                    i = 0
                    if isinstance(item[-2], TopoDS_Edge):
                        edge = item[-2]
                        i += 1
                    if n == i + 2:
                        d1 = d2 = item[0]
                    elif n == i + 3:
                        d1, d2 = item[0:2]
            else:
                face = item
            if isinstance(face, TopoDS_Edge) and d1 == d2:
                edge = face
                chamfer.Add(d1, edge)
            elif edge is None:
                for edge in child.topology.edges_from_face(face):
                    chamfer.Add(d1, d2, edge, face)
            else:
                chamfer.Add(d1, d2, edge, face)
        self.shape = chamfer.Shape()

    def chamfer_profile(self, child):
        """Use fillet with custom shape. Only supports 45 deg chamfers."""
        d = self.declaration
        if d.distance2:
            raise ValueError("Cannot mix profile and two distances")
        from OCCT.ChFi3d import ChFi3d_Linear

        builder = BRepFilletAPI_MakeFillet(child.shape)
        builder.SetFilletShape(ChFi3d_Linear)
        T = (tuple, list)
        for item in d.operations:
            if isinstance(item, T):
                if isinstance(item[0], T):
                    profile, edge = item
                    array = TColgp_Array1OfPnt2d(1, len(profile))
                    for i, pt in enumerate(profile):
                        array.SetValue(i + 1, gp_Pnt2d(*pt))
                    builder.Add(array, edge)
                elif len(item) == 2:
                    r, e = item
                    builder.Add(r, e)
                else:
                    raise ValueError("Cannot mix profile and two distances")
            else:
                builder.Add(d.distance, e)
        self.shape = builder.Shape()

    def set_distance(self, d):
        self.update_shape()

    def set_distance2(self, d):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()
