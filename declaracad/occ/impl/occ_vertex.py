"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import set_default
from enaml.colors import Color
from OCCT.Aspect import (
    Aspect_TOM_BALL,
    Aspect_TOM_O,
    Aspect_TOM_O_PLUS,
    Aspect_TOM_O_POINT,
    Aspect_TOM_O_STAR,
    Aspect_TOM_O_X,
    Aspect_TOM_PLUS,
    Aspect_TOM_POINT,
    Aspect_TOM_RING1,
    Aspect_TOM_RING2,
    Aspect_TOM_RING3,
    Aspect_TOM_STAR,
    Aspect_TOM_X,
)
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCCT.Prs3d import Prs3d_PointAspect

from declaracad.occ.draw import ProxyVertex

from .occ_shape import OccShape
from .utils import color_to_quantity_color

MARKERS = {
    "plus": Aspect_TOM_PLUS,
    "point": Aspect_TOM_POINT,
    "star": Aspect_TOM_STAR,
    "cross": Aspect_TOM_X,
    "circle": Aspect_TOM_O,
    "point-in-circle": Aspect_TOM_O_POINT,
    "star-in-circle": Aspect_TOM_O_STAR,
    "plus-in-circle": Aspect_TOM_O_PLUS,
    "cross-in-circle": Aspect_TOM_O_X,
    "large-ring": Aspect_TOM_RING1,
    "medium-ring": Aspect_TOM_RING2,
    "small-ring": Aspect_TOM_RING3,
    "ball": Aspect_TOM_BALL,
    "dot": Aspect_TOM_POINT,
}


class OccVertex(OccShape, ProxyVertex):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_vertex.html"
    )

    def create_shape(self):
        pt = self.declaration.position.proxy
        self.shape = BRepBuilderAPI_MakeVertex(pt).Vertex()

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        attrs = ais_shape.Attributes()
        color, alpha = color_to_quantity_color(d.color or Color())
        marker = MARKERS[d.marker]
        if aspect := attrs.PointAspect():
            aspect.SetColor(color)
            aspect.SetScale(d.marker_scale)
            aspect.SetTypeOfMarker(marker)
        else:
            aspect = Prs3d_PointAspect(marker, color, d.marker_scale)
        attrs.SetPointAspect(aspect)
        return ais_shape
