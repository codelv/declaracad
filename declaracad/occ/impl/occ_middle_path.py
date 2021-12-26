"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

@author: jrm
"""
from atom.api import set_default

from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeWire
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MiddlePath
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.TopoDS import TopoDS_Edge

from declaracad.occ.draw import ProxyMiddlePath
from .occ_wire import OccWire
from .occ_shape import Shape
from .topology import Topology


class OccMiddlePath(OccWire, ProxyMiddlePath):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_offset_a_p_i___middle_path.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        n = len(d.shapes)
        if n == 3:
            args = d.shapes
        elif n == 2:
            child = self.get_first_child()
            args = [child.shape] + d.shapes
        else:
            args = [c.shape for c in self.children]

        for i, s in enumerate(args[:]):
            if isinstance(s, Shape):
                s = args[i] = s.proxy.shape
            if isinstance(s, TopoDS_Edge):
                args[i] = BRepBuilderAPI_MakeWire(s).Wire()
        builder = BRepOffsetAPI_MiddlePath(*args)
        shape = Topology.cast_shape(builder.Shape())
        curve = self.curve = BRepAdaptor_CompCurve(shape)
        self.shape = shape

    def set_shapes(self, shapes):
        self.update_shape()
