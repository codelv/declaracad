"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 19, 2022

@author: jrm
"""
import io
import os
import warnings
from typing import Optional

from atom.api import Instance, Value, set_default
from OCCT.BRep import BRep_Builder
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)
from OCCT.Geom import Geom_BezierCurve
from OCCT.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
from OCCT.TColgp import TColgp_Array1OfPnt
from OCCT.TopoDS import TopoDS_Compound, TopoDS_Shape, TopoDS_Wire

from declaracad.core.utils import log

from ..draw import ProxyPdf
from .occ_shape import OccShape

try:
    from pdf4py.parser import Parser, SequentialParser
    from pdf4py.types import PDFOperator
except ImportError as e:
    warnings.warn(f"pdf4py could not be imported: {e}")
    Parser = object
    SequentialParser = object
    PDFOperator = None


IGNORED_CMDS = {
    "w",  # line width
    "J",  # line cap
    "j",  # line join
    "M",  # miter limit
    "d",  # dash phase
    "ri",  # rendering intent
    "i",  # flatness
    "ds",  # dict name
    # color stuff
    "cs",
    "CS",
    "sc",
    "SC",
    "scn",
    "SCN",
    "g",
    "G",
    "rg",
    "RG",
    "k",
    "K",
}

CLOSE_CMDS = ("h", "s", "b", "b*")
ENDPATH_CMDS = ("h", "s", "S", "f", "b", "b*")


def make_rect(x, y, w, h) -> BRepBuilderAPI_MakeWire:
    c0 = gp_Pnt(x, y)
    c1 = gp_Pnt(x + w, y)
    c2 = gp_Pnt(x + w, y + h)
    c3 = gp_Pnt(x, y + h)
    path = BRepBuilderAPI_MakeWire(
        BRepBuilderAPI_MakeEdge(c0, c1).Edge(),
        BRepBuilderAPI_MakeEdge(c1, c2).Edge(),
        BRepBuilderAPI_MakeEdge(c2, c3).Edge(),
        BRepBuilderAPI_MakeEdge(c3, c0).Edge(),
    )
    return c0, path


class OccPdf(OccShape, ProxyPdf):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_wire.html"
    )

    #: Make wire
    shape = Instance(TopoDS_Shape)

    #: The document
    doc = Instance(Parser)

    #: File
    f = Value()

    def create_shape(self):
        d = self.declaration
        if not d.source:
            return
        f = self.f
        if f is not None:
            f.close()
            self.f = None

        if os.path.exists(os.path.expanduser(d.source)):
            f = self.f = open(d.source, "rb")
        else:
            f = self.f = io.BytesIO()
            f.write(d.source)
            f.seek(0)

        doc = self.doc = Parser(f)
        root = doc.parse_reference(doc.trailer["Root"])
        pages = doc.parse_reference(root["Pages"])

        builder = BRep_Builder()
        shape = TopoDS_Compound()
        builder.MakeCompound(shape)

        for item in pages["Kids"]:
            page = doc.parse_reference(item)
            for s in self.extract_shapes(doc, page):
                builder.Add(shape, s)

        if d.scale != 1:
            bbox = self.get_bounding_box(shape)
            t = gp_Trsf()
            t.SetScale(gp_Pnt(*bbox.center), d.scale)
            shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

        if d.center:
            bbox = self.get_bounding_box(shape)
            x, y, z = bbox.center
            t = gp_Trsf()
            t.SetTranslation(gp_Vec(-x, -y, 0))
            shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

        if d.mirror:
            bbox = self.get_bounding_box(shape)
            t = gp_Trsf()
            t.SetMirror(gp_Ax2(gp_Pnt(*bbox.center), gp_Dir(0, 1, 0)))
            shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

        t = self.get_transform()
        shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

        self.shape = shape

    def set_source(self, source):
        self.create_shape()

    def set_mirror(self, mirror):
        self.create_shape()

    def set_fill_mode(self, mode):
        self.create_shape()

    def set_center(self, center):
        self.create_shape()

    def extract_shapes(self, doc, page):
        """Parse shapes from the pdf page"""
        assert page.get("Type", "Type") == "Page"
        media_box = page["MediaBox"]
        log.debug(f"pdf media box: {media_box}")
        contents = doc.parse_reference(page["Contents"])
        data = contents.stream()
        path: Optional[BRepBuilderAPI_MakeWire] = None
        params = []
        stack = []
        d = self.declaration
        ctm = gp_Trsf()

        last_pnt = gp_Pnt()
        start_pnt: Optional[gp_Pnt] = None
        tol = self.declaration.tolerance
        for token in SequentialParser(data):
            if not isinstance(token, PDFOperator):
                params.append(token)
                continue
            cmd = token.value
            if cmd == "q":
                stack.append(ctm)
                ctm = gp_Trsf().Multiplied(ctm)
            elif cmd == "Q":
                ctm = stack.pop()  # If this fails the pdf is invalid
            elif cmd in IGNORED_CMDS:
                pass  # no-op
            elif cmd == "cm":
                a, b, c, d, e, f = params
                log.info(params)
                matrix = gp_Trsf()
                matrix.SetValues(
                    a,
                    b,
                    0,
                    e,
                    c,
                    d,
                    0,
                    f,
                    0,
                    0,
                    1,
                    0,
                )
                ctm = ctm.Multiplied(matrix)
            elif cmd == "m":
                assert path is None
                path = BRepBuilderAPI_MakeWire()
                x, y = params
                last_pnt = start_pnt = gp_Pnt(x, y, 0)
            elif cmd == "re":
                assert path is None
                last_pnt, path = make_rect(*params)
                yield BRepBuilderAPI_Transform(path.Wire(), ctm).Shape()
                path = None
            elif cmd in "l":
                # Line to
                x, y = params
                pnt = gp_Pnt(x, y, 0)
                if not last_pnt.IsEqual(pnt, tol):
                    path.Add(BRepBuilderAPI_MakeEdge(last_pnt, pnt).Edge())
                last_pnt = pnt
            elif cmd == "c":
                # Cubic to
                pts = TColgp_Array1OfPnt(1, 4)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                pts.SetValue(3, gp_Pnt(params[2], params[3], 0))
                last_pnt = gp_Pnt(params[4], params[5], 0)
                pts.SetValue(4, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd in ("v", "y"):
                # Quad to
                pts = TColgp_Array1OfPnt(1, 3)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                last_pnt = gp_Pnt(params[2], params[3], 0)
                pts.SetValue(3, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd == "n":
                path = None
            elif cmd in ENDPATH_CMDS:
                if path is not None:
                    if cmd in CLOSE_CMDS and not last_pnt.IsEqual(start_pnt, tol):
                        path.Add(BRepBuilderAPI_MakeEdge(last_pnt, start_pnt).Edge())
                    yield BRepBuilderAPI_Transform(path.Wire(), ctm).Shape()
                    path = None
                    start_pnt = None
            else:
                log.warning(f"pdf command ignored: {cmd} {params}")

            # Reset
            params = []
