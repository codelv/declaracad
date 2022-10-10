"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from OCCT.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeCylinder

from declaracad.occ.shape import ProxyTube

from .occ_shape import OccShape, coerce_axis


class OccTube(OccShape, ProxyTube):
    def create_shape(self):
        d = self.declaration
        outer_radius = max(d.radius, d.radius2)
        inner_radius = min(d.radius, d.radius2)

        args = [coerce_axis(d.axis), outer_radius, d.height]
        if d.angle:
            args.append(d.angle)
        shape = BRepPrimAPI_MakeCylinder(*args).Shape()

        if inner_radius > 0:
            args[1] = inner_radius
            inner_cylinder = BRepPrimAPI_MakeCylinder(*args).Shape()
            shape = BRepAlgoAPI_Cut(shape, inner_cylinder).Shape()
        self.shape = shape

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_angle(self, angle):
        self.create_shape()

    def set_height(self, height):
        self.create_shape()
