"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""

from atom.api import Instance
from OCCT.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCCT.gp import gp_Ax1, gp_Ax2, gp_Ax3, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

from declaracad.occ.algo import Mirror, ProxyTransform, Rotate, Scale, Translate

from .occ_algo import OccOperation, coerce_shape
from .occ_shape import DEFAULT_AXIS, OccShape
from .topology import Topology


class OccTransform(OccOperation, ProxyTransform):
    reference = "https://dev.opencascade.org/doc/refman/html/classgp___trsf.html"

    _old_shape = Instance(OccShape)

    def get_transform(self):
        d = self.declaration
        result = gp_Trsf()
        if d.operations:
            for op in d.operations:
                t = gp_Trsf()
                if isinstance(op, Translate):
                    t.SetTranslation(gp_Vec(op.x, op.y, op.z))
                elif isinstance(op, Rotate):
                    t.SetRotation(
                        gp_Ax1(gp_Pnt(*op.point), gp_Dir(*op.direction)), op.angle
                    )
                elif isinstance(op, Mirror):
                    Ax = gp_Ax2 if op.plane else gp_Ax1
                    t.SetMirror(Ax(gp_Pnt(*op.point), gp_Dir(op.x, op.y, op.z)))
                elif isinstance(op, Scale):
                    t.SetScale(gp_Pnt(*op.point), op.s)
                result.Multiply(t)
        else:
            axis = gp_Ax3(d.position.proxy, d.direction.proxy)
            axis.Rotate(axis.Axis(), d.rotation)
            result.SetDisplacement(DEFAULT_AXIS, axis)
        return result

    def update_shape(self, change=None):
        d = self.declaration

        #: Get the shape to apply the tranform to
        if d.shape:
            original = coerce_shape(d.shape)
        else:
            # Use the first child
            child = self.get_first_child()
            if child is None:
                raise ValueError("Transform has no shape to transform %s" % d)
            original = child.shape

        t = self.get_transform()
        transform = BRepBuilderAPI_Transform(original, t, True)

        # Convert it back to the original type
        self.shape = Topology.cast_shape(transform.Shape())

    def set_shape(self, shape):
        if self._old_shape:
            self._old_shape.unobserve("shape", self.update_shape)
        self._old_shape = shape.proxy
        self._old_shape.observe("shape", self.update_shape)

    def set_translate(self, translation):
        self.update_shape()

    def set_rotate(self, rotation):
        self.update_shape()

    def set_scale(self, scale):
        self.update_shape()

    def set_mirror(self, axis):
        self.update_shape()
