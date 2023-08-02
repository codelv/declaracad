"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 24, 2021

@author: jrm
"""
import os

from atom.api import Typed, set_default
from OCCT import Graphic3d
from OCCT.Font import (
    Font_BRepFont,
    Font_BRepTextBuilder,
    Font_FA_Regular,
    Font_FontAspect,
    Font_FontMgr,
)
from OCCT.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCCT.gp import gp_Ax3, gp_Trsf, gp_Vec
from OCCT.NCollection import NCollection_String
from OCCT.TCollection import TCollection_AsciiString

from declaracad.occ.draw import ProxyText

from .occ_shape import OccShape, coerce_axis

#: Track registered fonts
FONT_MANAGER = Font_FontMgr.GetInstance_()
FONT_REGISTRY: set[str] = set()
FONT_CACHE: dict[tuple[str, str, float], Font_BRepFont] = {}


class OccText(OccShape, ProxyText):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/class_topo_d_s___shape.html"
    )

    builder = Typed(Font_BRepTextBuilder, ())

    font = Typed(Font_BRepFont)

    def update_font(self, change=None):
        self.font = self._default_font()

    def _default_font(self):
        d = self.declaration
        font_family = d.font
        if (
            font_family
            and os.path.exists(font_family)
            and font_family not in FONT_REGISTRY
        ):
            FONT_MANAGER.RegisterFont(font_family, True)
            FONT_REGISTRY.add(font_family)

        attr = "Font_FA_{}".format(d.style.title().replace("-", ""))
        font_style = getattr(Font_FontAspect, attr, Font_FA_Regular)

        # Fonts are cached by OpenCASCADE so we also cache the here or
        # each time the font instance is released by python it get's lost
        key = (font_family, d.style, d.size)
        font = FONT_CACHE.get(key)
        if font is None:
            font_name = TCollection_AsciiString(font_family)
            font = Font_BRepFont()
            assert font.FindAndInit(font_name, font_style, float(d.size))
            FONT_CACHE[key] = font
        return font

    def create_shape(self):
        """Create the shape by loading it from the given path."""
        d = self.declaration
        axis = gp_Ax3(coerce_axis(d.axis))
        attr = "Graphic3d_HTA_{}".format(d.horizontal_alignment.upper())
        halign = getattr(Graphic3d, attr)
        attr = "Graphic3d_VTA_{}".format(d.vertical_alignment.upper())
        valign = getattr(Graphic3d, attr)
        text = NCollection_String(d.text.encode("utf-8"))
        shape = self.builder.Perform(self.font, text, axis, halign, valign)
        if d.center:
            bbox = self.get_bounding_box(shape)
            x, y, z = bbox.center
            t = gp_Trsf()
            t.SetTranslation(gp_Vec(-x, -y, 0))
            shape = BRepBuilderAPI_Transform(shape, t).Shape()
        self.shape = shape


    def set_text(self, text: str):
        self.create_shape()

    def set_font(self, font: str):
        self.update_font()
        self.create_shape()

    def set_size(self, size: float):
        self.update_font()
        self.create_shape()

    def set_style(self, style: str):
        self.update_font()
        self.create_shape()

    def set_composite(self, composite: bool):
        self.create_shape()

    def set_vertical_alignment(self, alignment: str):
        self.create_shape()

    def set_horizontal_alignment(self, alignment: str):
        self.create_shape()
