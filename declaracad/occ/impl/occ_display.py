"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 27, 2020

@author: jrm
"""
from atom.api import Instance, Typed
from OCCT.AIS import AIS_InteractiveObject, AIS_Line, AIS_Plane, AIS_TextLabel
from OCCT.Geom import Geom_Axis2Placement, Geom_Line, Geom_Plane
from OCCT.gp import gp_Ax2
from OCCT.Graphic3d import (
    Graphic3d_Group,
    Graphic3d_MaterialAspect,
    Graphic3d_NOM_BRASS,
    Graphic3d_Text,
)
from OCCT.Prs3d import Prs3d_Arrow
from OCCT.TCollection import TCollection_ExtendedString

from declaracad.core.utils import log

from ..display import (
    ProxyDisplayArrow,
    ProxyDisplayItem,
    ProxyDisplayLine,
    ProxyDisplayPlane,
    ProxyDisplayText,
)
from ..shape import Point
from .occ_shape import coerce_axis
from .utils import color_to_quantity_color


class AIS_Arrow(AIS_InteractiveObject):
    def __init__(
        self,
        axis,
        tube_radius,
        axis_length,
        cone_radius,
        cone_length,
        number_of_facetts=360,
    ):
        super().__init__()
        self.params = (
            axis,
            tube_radius,
            axis_length,
            cone_radius,
            cone_length,
            int(number_of_facetts),
        )
        self.SetInfiniteState(True)

    def Compute(self, prs_mgr, pres, mode):
        group = pres.CurrentGroup()
        handle = Prs3d_Arrow.DrawShaded_(*self.params)
        group.SetPrimitivesAspect(self.Attributes().ShadingAspect().Aspect())
        group.__class__ = Graphic3d_Group  # Hack?
        group.AddPrimitiveArray(handle)

    def ComputeSelection(self, pres, mode):
        pass

    def SetColor(self, color):
        drawer = self.Attributes()
        sa = drawer.ShadingAspect()
        a = sa.Aspect()
        a.SetColor(color)
        a.SetInteriorColor(color)
        ma = Graphic3d_MaterialAspect(Graphic3d_NOM_BRASS)
        ma.SetColor(color)
        a.SetFrontMaterial(ma)
        drawer.SetShadingAspect(sa)


class OccDisplayItem(ProxyDisplayItem):
    # -------------------------------------------------------------------------
    # Initialization API
    # -------------------------------------------------------------------------
    def create_item(self, context):
        pass

    def update_item(self):
        """Recreates the dimension catching any errors"""
        if not self.context:
            return
        try:
            self.create_item(self.context)
        except Exception as e:
            log.exception(e)

    def activate_top_down(self):
        """Activate the proxy for the top-down pass."""
        self.create_item()

    def activate_bottom_up(self):
        """Activate the proxy tree for the bottom-up pass."""
        pass

    def update_color(self, ais_item):
        d = self.declaration
        color, alpha = color_to_quantity_color(d.color)
        ais_item.SetColor(color)
        ais_item.SetTransparency(d.transparency)

    # -------------------------------------------------------------------------
    # Proxy API
    # -------------------------------------------------------------------------
    def set_position(self, position):
        self.update_item()

    def set_color(self, color):
        self.update_item()

    def set_direction(self, direction):
        self.update_item()


class OccDisplayLine(OccDisplayItem, ProxyDisplayLine):
    #: A reference to the toolkit item created by the proxy.
    item = Typed(AIS_Line)

    def create_item(self):
        d = self.declaration
        line = Geom_Line(d.position.proxy, d.direction.proxy)
        ais_item = AIS_Line(line)
        color, alpha = color_to_quantity_color(d.color)
        ais_item.SetColor(color)
        self.item = ais_item


class OccDisplayPlane(OccDisplayItem, ProxyDisplayPlane):
    #: A reference to the toolkit item created by the proxy.
    item = Typed(AIS_Plane)

    def create_item(self):
        d = self.declaration
        plane = Geom_Plane(d.position.proxy, d.direction.proxy)
        ais_item = AIS_Plane(plane)
        self.update_color(ais_item)
        self.item = ais_item


class OccDisplayArrow(OccDisplayItem, ProxyDisplayArrow):
    #: A reference to the toolkit item created by the proxy.
    item = Typed(AIS_Arrow)

    def create_item(self):
        d = self.declaration
        axis = coerce_axis((d.position, d.direction, 0))
        ais_item = AIS_Arrow(axis.Axis(), *d.tube_size, *d.cone_size)
        self.update_color(ais_item)
        self.item = ais_item

    def set_cone_size(self, size):
        self.create_item()

    def set_tube_size(self, size):
        self.create_item()


class OccDisplayText(OccDisplayItem, ProxyDisplayText):
    #: A reference to the toolkit item created by the proxy.
    item = Typed(AIS_TextLabel)

    def create_item(self):
        d = self.declaration
        text = TCollection_ExtendedString(d.text)
        ais_item = AIS_TextLabel()
        ais_item.SetText(text)
        ais_item.SetPosition(d.position.proxy)
        ais_item.SetHeight(d.size)
        if d.font:
            ais_item.SetFont(d.font)
        self.update_color(ais_item)
        self.item = ais_item

    def set_text(self, text):
        self.update_item()

    def set_size(self, size):
        self.update_item()

    def set_font(self, font):
        self.update_item()
