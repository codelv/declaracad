"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 20, 2018

@author: jrm
"""

import os
import re
import warnings
from math import cos, pi, radians, sin, sqrt, tan
from xml.etree import ElementTree as etree

from atom.api import Atom, Dict, ForwardTyped, Instance, Str
from OCCT.BRep import BRep_Builder
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon,
    BRepBuilderAPI_MakeWire,
    BRepBuilderAPI_Transform,
)

# from OCCT.BRepLib import breplib_BuildCurves3d
from OCCT.GC import GC_MakeArcOfEllipse
from OCCT.Geom import Geom_BezierCurve
from OCCT.gp import (
    gp_Ax1,
    gp_Ax2,
    gp_Circ,
    gp_Dir,
    gp_Elips,
    gp_Pnt,
    gp_Pnt2d,
    gp_Trsf,
    gp_Trsf2d,
    gp_Vec,
)
from OCCT.TColgp import TColgp_Array1OfPnt
from OCCT.TopoDS import TopoDS_Compound, TopoDS_Shape

from declaracad.core.utils import log

from ..draw import ProxySvg
from .occ_shape import OccShape

Z_DIR = gp_Dir(0, 0, 1)
NEG_Z_DIR = gp_Dir(0, 0, -1)
Z_AXIS = gp_Ax1(gp_Pnt(0, 0, 0), Z_DIR)

UNITS = {
    "in": 90.0,
    "pt": 1.25,
    "px": 1,
    "mm": 3.5433070866,
    "cm": 35.433070866,
    "m": 3543.3070866,
    "km": 3543307.0866,
    "pc": 15.0,
    "yd": 3240,
    "ft": 1080,
}

# From  simplepath.py's parsePath by Aaron Spike, aaron@ekips.org
PATHDEFS = {
    "M": ["L", 2, [float, float], ["x", "y"]],
    "L": ["L", 2, [float, float], ["x", "y"]],
    "H": ["H", 1, [float], ["x"]],
    "V": ["V", 1, [float], ["y"]],
    "C": [
        "C",
        6,
        [float, float, float, float, float, float],
        ["x", "y", "x", "y", "x", "y"],
    ],
    "S": ["S", 4, [float, float, float, float], ["x", "y", "x", "y"]],
    "Q": ["Q", 4, [float, float, float, float], ["x", "y", "x", "y"]],
    "T": ["T", 2, [float, float], ["x", "y"]],
    "A": [
        "A",
        7,
        [float, float, float, int, int, float, float],
        ["r", "r", "a", "a", "s", "x", "y"],
    ],
    "Z": ["L", 0, [], []],
}


def parse_unit(value):
    """Returns userunits given a string representation of units
    in another system
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    unit = re.compile("(%s)$" % "|".join(UNITS.keys()))
    param = re.compile(r"(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)")

    p = param.match(value)
    u = unit.search(value)
    if p:
        retval = float(p.string[p.start() : p.end()])
    else:
        retval = 0.0
    if u:
        try:
            return retval * UNITS[u.string[u.start() : u.end()]]
        except KeyError:
            pass
    return retval


def make_ellipse(p, rx, ry, rotate=0, direction=Z_DIR):
    """gp_Elips doesn't allow minor > major so swap and rotate instead if
    that's the case.
    """
    c = gp_Pnt(*p)
    if ry > rx:
        rx, ry = ry, rx  # Swap
        rotate += pi / 2
        # This only works when rotate == 0
    ellipse = gp_Elips(gp_Ax2(c, direction), rx, ry)
    ellipse.Rotate(gp_Ax1(c, direction), rotate)
    return ellipse


def compute_arc_center(x1, y1, rx, ry, phi, large_arc_flag, sweep_flag, x2, y2):
    """Compute center point of an arc based SVG parameters given.
    Thanks to Arnout Engelen's work in Inkcut.

    Notes
    -----
    See https://www.w3.org/TR/SVG/implnote.html F.6.6

    """
    rx = abs(rx)
    ry = abs(ry)

    # https://www.w3.org/TR/SVG/implnote.html F.6.5
    x1prime = cos(phi) * (x1 - x2) / 2 + sin(phi) * (y1 - y2) / 2
    y1prime = -sin(phi) * (x1 - x2) / 2 + cos(phi) * (y1 - y2) / 2

    # https://www.w3.org/TR/SVG/implnote.html F.6.6
    lamb = (x1prime * x1prime) / (rx * rx) + (y1prime * y1prime) / (ry * ry)
    if lamb >= 1:
        ry = sqrt(lamb) * ry
        rx = sqrt(lamb) * rx

    # Back to https://www.w3.org/TR/SVG/implnote.html F.6.5
    radicand = (
        rx * rx * ry * ry - rx * rx * y1prime * y1prime - ry * ry * x1prime * x1prime
    )
    radicand /= rx * rx * y1prime * y1prime + ry * ry * x1prime * x1prime

    if radicand < 0:
        radicand = 0

    factor = (-1 if large_arc_flag == sweep_flag else 1) * sqrt(radicand)

    cxprime = factor * rx * y1prime / ry
    cyprime = -factor * ry * x1prime / rx

    cx = cxprime * cos(phi) - cyprime * sin(phi) + (x1 + x2) / 2
    cy = cxprime * sin(phi) + cyprime * cos(phi) + (y1 + y2) / 2
    # if phi == 0:
    # start_theta = -atan2((y1 - cy) * rx, (x1 - cx) * ry)

    # start_phi = -atan2(y1 - cy, x1 - cx)
    # end_phi = -atan2(y2 - cy, x2 - cx)

    # sweep_length = end_phi - start_phi

    # if sweep_length < 0 and not sweep_flag:
    # sweep_length += 2 * pi
    # elif sweep_length > 0 and sweep_flag:
    # sweep_length -= 2 * pi

    # self.arcTo(cx - rx, cy - ry, rx * 2, ry * 2,
    # start_theta * 360 / 2 / pi, sweep_length * 360 / 2 / pi)
    return (cx, cy, rx, ry)


class OccSvgNode(Atom):
    svg = ForwardTyped(lambda: OccSvg)

    #: Transform
    transform = Instance(gp_Trsf, ())

    #: Element
    element = Instance(etree.Element)

    #: Parsed style fields
    style = Dict()

    #: Fill color
    fill = Str()

    def create_shape(self):
        """Create and return the shape for the given svg node."""
        raise NotImplementedError

    def _default_style(self):
        style = {}
        style_attr = self.element.attrib.get("style", "")
        if style_attr:
            for it in style_attr.split(";"):
                k, v = it.strip().split(":", 1)
                style[k.strip()] = v.strip()
        return style

    def _default_fill(self):
        fill = self.element.attrib.get("fill", None)
        if fill is None:
            fill = self.style.get("fill", None)
        if fill and fill != "transparent":
            return fill
        return ""

    def _default_transform(self):
        transform = self.element.attrib.get("transform", None)
        t = gp_Trsf()
        if not transform:
            return t
        pattern = r"([A-z]+)\s*\(\s*((?:\-?\d+\.?\d*\s*[%a-z]*,?\s*)+)\s*\)"
        for m in re.finditer(pattern, transform):
            cmd, args = m.groups()
            try:
                args = args.replace(",", " ")
                args = [parse_unit(arg) for arg in args.split(" ")]
                if cmd == "matrix":
                    a, b, c, d, e, f = args
                    matrix = gp_Trsf2d()
                    matrix.SetValues(a, c, e, b, d, f)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "matrix3d":
                    matrix = gp_Trsf()
                    matrix.SetValues(*args)
                    t.Multiply(matrix)
                elif cmd == "rotate":
                    if len(args) == 3:
                        a, x, y = args
                    else:
                        x = y = 0
                        a = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetRotation(gp_Pnt2d(x, y), radians(a))
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "translate":
                    if len(args) == 2:
                        x, y = args
                    else:
                        x, y = args[0], 0
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, 0, x, 0, 1, y)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "translateX":
                    x = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, 0, x, 0, 1, 0)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "translateY":
                    y = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, 0, 0, 0, 1, y)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "scale":
                    if len(args) == 2:
                        x, y = args
                    else:
                        x = y = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(x, 0, 0, 0, y, 0)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "scaleX":
                    x = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(x, 0, 0, 0, 1, 0)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "scaleY":
                    y = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, 0, 0, 0, y, 0)
                    t.Multiply(gp_Trsf(matrix))
                # elif cmd == 'scaleZ':
                #    z = args[0]
                #    matrix = gp_Trsf2d()
                #    matrix.SetValues(
                #        1, 0, 0,
                #        0, 1, 0,
                #        0, 0, z)
                #    t.Multiply(gp_Trsf(matrix))
                # elif cmd == 'scale3d':
                #    x, y, z = args[0]
                #    matrix = gp_Trsf2d()
                #    matrix.SetValues(
                #        x, 0, 0,
                #        0, y, 0,
                #        0, 0, z)
                #    t.Multiply(gp_Trsf(matrix))
                elif cmd == "skew":
                    x, y = args
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, tan(radians(x)), 0, tan(radians(y)), 1, 0)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "skewX":
                    x = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, tan(radians(x)), 0, 0, 1, 0)
                    t.Multiply(gp_Trsf(matrix))
                elif cmd == "skewY":
                    y = args[0]
                    matrix = gp_Trsf2d()
                    matrix.SetValues(1, 0, 0, tan(radians(y)), 1, 0)
                    t.Multiply(gp_Trsf(matrix))
                else:
                    # TODO: ...
                    warnings.warn(f"Unsupported transform {cmd}")
            except RuntimeError as e:
                log.warning(f"Failed to handled transform {cmd} {args}")
                log.exception(e)
        return t

    def fill_shape(self, wire):
        fill_mode = self.svg.declaration.fill_mode
        if fill_mode == "always" or (fill_mode == "auto" and self.fill):
            return BRepBuilderAPI_MakeFace(wire).Face()
        return wire


class OccSvgEllipse(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        cx = parse_unit(attrs.get("cx", 0))
        cy = parse_unit(attrs.get("cy", 0))
        rx = parse_unit(attrs.get("rx", 0))
        ry = parse_unit(attrs.get("ry", 0))
        ellipse = make_ellipse((cx, cy, 0), rx, ry)
        edge = BRepBuilderAPI_MakeEdge(ellipse).Edge()
        return self.fill_shape(BRepBuilderAPI_MakeWire(edge).Wire())


class OccSvgCircle(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        cx = parse_unit(attrs.get("cx", 0))
        cy = parse_unit(attrs.get("cy", 0))
        r = parse_unit(attrs.get("r", 0))
        circle = gp_Circ(gp_Ax2(gp_Pnt(cx, cy, 0), Z_DIR), r)
        edge = BRepBuilderAPI_MakeEdge(circle).Edge()
        return self.fill_shape(BRepBuilderAPI_MakeWire(edge).Wire())


class OccSvgLine(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        x1 = parse_unit(attrs.get("x1", 0))
        y1 = parse_unit(attrs.get("y1", 0))
        x2 = parse_unit(attrs.get("x2", 0))
        y2 = parse_unit(attrs.get("y2", 0))
        p1 = gp_Pnt(x1, y1, 0)
        p2 = gp_Pnt(x2, y2, 0)
        return BRepBuilderAPI_MakeEdge(p1, p2).Edge()


class OccSvgRect(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        x = parse_unit(attrs.get("x", 0))
        y = parse_unit(attrs.get("y", 0))
        w = parse_unit(attrs.get("width", 0))
        h = parse_unit(attrs.get("height", 0))
        rx = parse_unit(attrs.get("rx", 0))
        ry = parse_unit(attrs.get("ry", 0))
        if rx == ry == 0:
            shape = BRepBuilderAPI_MakePolygon(
                gp_Pnt(x, y, 0),
                gp_Pnt(x + w, y, 0),
                gp_Pnt(x + w, y + h, 0),
                gp_Pnt(x, y + h, 0),
                True,
            )
            return self.fill_shape(shape.Wire())
        elif rx == 0:
            rx = ry
        elif ry == 0:
            ry = rx

        # Build the rect
        shape = BRepBuilderAPI_MakeWire()

        # Bottom
        p1 = gp_Pnt(x + rx, y, 0)
        p2 = gp_Pnt(x + w - rx, y, 0)

        # Right
        p3 = gp_Pnt(x + w, y + ry, 0)
        p4 = gp_Pnt(x + w, y + h - ry, 0)

        # Top
        p5 = gp_Pnt(x + w - rx, y + h, 0)
        p6 = gp_Pnt(x + rx, y + h, 0)

        # Left
        p7 = gp_Pnt(x, y + h - ry, 0)
        p8 = gp_Pnt(x, y + ry, 0)

        # Bottom
        shape.Add(BRepBuilderAPI_MakeEdge(p1, p2).Edge())

        # Arc bottom right
        c = make_ellipse((x + w - rx, y + ry, 0), rx, ry)
        shape.Add(
            BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p2, p3, False).Value()
            ).Edge()
        )

        # Right
        shape.Add(BRepBuilderAPI_MakeEdge(p3, p4).Edge())

        # Arc top right
        c.SetLocation(gp_Pnt(x + w - rx, y + h - ry, 0))
        shape.Add(
            BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p4, p5, False).Value()
            ).Edge()
        )

        # Top
        shape.Add(BRepBuilderAPI_MakeEdge(p5, p6).Edge())

        # Arc top left
        c.SetLocation(gp_Pnt(x + rx, y + h - ry, 0))
        shape.Add(
            BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p6, p7, False).Value()
            ).Edge()
        )

        # Left
        shape.Add(BRepBuilderAPI_MakeEdge(p7, p8).Edge())

        # Arc bottom left
        c.SetLocation(gp_Pnt(x + rx, y + ry, 0))
        shape.Add(
            BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p8, p1, False).Value()
            ).Edge()
        )

        wire = shape.Wire()
        wire.Closed(True)
        return self.fill_shape(wire)


class OccSvgPath(OccSvgNode):
    def path_lexer(self, d):
        """
        From  simplepath.py's parsePath by Aaron Spike, aaron@ekips.org

        returns and iterator that breaks path data
        identifies cmd and parameter tokens
        """
        offset = 0
        length = len(d)
        delim = re.compile(r"[ \t\r\n,]+")
        cmd = re.compile(r"[MLHVCSQTAZmlhvcsqtaz]")
        parameter = re.compile(
            r"(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)"
        )
        while True:
            m = delim.match(d, offset)
            if m:
                offset = m.end()
            if offset >= length:
                break
            m = cmd.match(d, offset)
            if m:
                yield [d[offset : m.end()], True]
                offset = m.end()
                continue
            m = parameter.match(d, offset)
            if m:
                yield [d[offset : m.end()], False]
                offset = m.end()
                continue
            raise ValueError("Invalid path data at %s!" % offset)

    def parse_path(self, d):
        """
        From  simplepath.py's parsePath by Aaron Spike, aaron@ekips.org

        Parse SVG path and return an array of segments.
        Removes all shorthand notation.
        Converts coordinates to absolute.
        """
        lexer = self.path_lexer(d)

        pen = (0.0, 0.0)
        sub_path_start = pen
        last_control = pen
        last_cmd = ""

        while True:
            try:
                token, is_cmd = next(lexer)
            except StopIteration:
                break
            params = []
            need_param = True
            if is_cmd:
                if not last_cmd and token.upper() != "M":
                    raise ValueError(
                        "Invalid path, must begin with moveto ("
                        "M or m), given %s." % last_cmd
                    )
                else:
                    cmd = token
            else:
                # cmd was omited
                # use last cmd's implicit next cmd
                need_param = False
                if last_cmd:
                    if last_cmd.isupper():
                        cmd = PATHDEFS[last_cmd][0]
                    else:
                        cmd = PATHDEFS[last_cmd.upper()][0].lower()
                else:
                    raise ValueError("Invalid path, no initial cmd.")
            num_params = PATHDEFS[cmd.upper()][1]
            while num_params > 0:
                if need_param:
                    try:
                        token, is_cmd = next(lexer)
                        if is_cmd:
                            raise ValueError(
                                "Invalid number of parameters " "for %s" % (cmd,)
                            )
                    except StopIteration:
                        raise Exception("Unexpected end of path")
                cast = PATHDEFS[cmd.upper()][2][-num_params]
                param = cast(token)
                if cmd.islower():
                    if PATHDEFS[cmd.upper()][3][-num_params] == "x":
                        param += pen[0]
                    elif PATHDEFS[cmd.upper()][3][-num_params] == "y":
                        param += pen[1]
                params.append(param)
                need_param = True
                num_params -= 1
            # segment is now absolute so
            output_cmd = cmd.upper()

            # Flesh out shortcut notation
            if output_cmd in ("H", "V"):
                if output_cmd == "H":
                    params.append(pen[1])
                if output_cmd == "V":
                    params.insert(0, pen[0])
                output_cmd = "L"
            if output_cmd in ("S", "T"):
                params.insert(0, pen[1] + (pen[1] - last_control[1]))
                params.insert(0, pen[0] + (pen[0] - last_control[0]))
                if output_cmd == "S":
                    output_cmd = "C"
                if output_cmd == "T":
                    output_cmd = "Q"

            # current values become "last" values
            if output_cmd == "M":
                sub_path_start = tuple(params[0:2])
                pen = sub_path_start
            if output_cmd == "Z":
                pen = sub_path_start
            else:
                pen = tuple(params[-2:])

            if output_cmd in ("Q", "C"):
                last_control = tuple(params[-4:-2])
            else:
                last_control = pen

            last_cmd = cmd

            yield (output_cmd, params)

    def create_shape(self):
        data = self.element.attrib.get("d")
        shapes = []
        path = None
        tol = 1e-6
        for cmd, params in self.parse_path(data):
            if cmd == "M":
                if path is not None:
                    shapes.append(path.Wire())
                path = BRepBuilderAPI_MakeWire()
                last_pnt = gp_Pnt(params[0], params[1], 0)
                start_pnt = last_pnt
            elif cmd in ["L", "H", "V"]:
                pnt = gp_Pnt(params[0], params[1], 0)
                if not last_pnt.IsEqual(pnt, tol):
                    path.Add(BRepBuilderAPI_MakeEdge(last_pnt, pnt).Edge())
                last_pnt = pnt
            elif cmd == "Q":
                # Quadratic Bezier
                pts = TColgp_Array1OfPnt(1, 3)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                last_pnt = gp_Pnt(params[2], params[3], 0)
                pts.SetValue(3, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd == "C":
                # Cubic Bezier
                pts = TColgp_Array1OfPnt(1, 4)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                pts.SetValue(3, gp_Pnt(params[2], params[3], 0))
                last_pnt = gp_Pnt(params[4], params[5], 0)
                pts.SetValue(4, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd == "A":
                # Warning: Play at your own risk!
                x1, y1 = last_pnt.X(), last_pnt.Y()
                rx, ry, phi, large_arc_flag, sweep_flag, x2, y2 = params
                phi = radians(phi)
                pnt = gp_Pnt(x2, y2, 0)
                cx, cy, rx, ry = compute_arc_center(
                    x1, y1, rx, ry, phi, large_arc_flag, sweep_flag, x2, y2
                )
                z_dir = Z_DIR if sweep_flag else NEG_Z_DIR  # sweep_flag
                c = make_ellipse((cx, cy, 0), rx, ry, phi, z_dir)
                curve = GC_MakeArcOfEllipse(c, last_pnt, pnt, True).Value()
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
                last_pnt = pnt
            elif cmd == "Z":
                if not last_pnt.IsEqual(start_pnt, tol):
                    edge = BRepBuilderAPI_MakeEdge(last_pnt, start_pnt).Edge()
                    path.Add(edge)
                shapes.append(self.fill_shape(path.Wire()))
                path = None  # Close path
                last_pnt = start_pnt
        if path is not None:
            shape = path.Wire()
            if last_pnt.IsEqual(start_pnt, tol):
                shape = self.fill_shape(shape)
            shapes.append(shape)

        return shapes


class OccSvgPolyline(OccSvgNode):
    @property
    def points(self):
        return self.element.attrib.get("points", "")

    def create_shape(self):
        shape = BRepBuilderAPI_MakePolygon()
        for m in re.finditer(r"(\-?\d+\.?\d*),(\-?\d+\.?\d*)\s+", self.points):
            x, y = map(float, m.groups())
            shape.Add(gp_Pnt(x, y, 0))
        return shape.Wire()


class OccSvgPolygon(OccSvgNode):
    @property
    def points(self):
        return self.element.attrib.get("points", "")

    def create_shape(self):
        shape = BRepBuilderAPI_MakePolygon()
        for m in re.finditer(r"(\-?\d+\.?\d*),(\-?\d+\.?\d*)\s+", self.points):
            x, y = map(float, m.groups())
            shape.Add(gp_Pnt(x, y, 0))
        shape.Close()
        return self.fill_shape(shape.Wire())


class OccSvgGroup(OccSvgNode):
    # Do not warn for these
    excluded_tags = (
        "{http://www.w3.org/2000/svg}defs",
        "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}namedview",
        "{http://www.w3.org/2000/svg}metadata",
    )

    def create_shape(self):
        shapes = []
        t = self.transform
        for e in self.element:
            tag = e.tag
            if not isinstance(tag, str):
                continue  # Comment
            if not tag.startswith("{"):
                tag = "{http://www.w3.org/2000/svg}%s" % tag
            OccNode = SVG_NODES.get(tag)
            if OccNode is None:
                if tag not in self.excluded_tags:
                    warnings.warn("SVG tag %s is not yet supported." % tag)
                continue
            node = OccNode(element=e, svg=self.svg)
            result = node.create_shape()
            trsf = node.transform.Multiplied(t)
            if not isinstance(result, list):
                result = [result]
            for s in result:
                shapes.append(BRepBuilderAPI_Transform(s, trsf, True).Shape())
        return shapes


class OccSvgDoc(OccSvgGroup):
    """TODO: Handle transforms"""


SVG_NODES = {
    "{http://www.w3.org/2000/svg}ellipse": OccSvgEllipse,
    "{http://www.w3.org/2000/svg}circle": OccSvgCircle,
    "{http://www.w3.org/2000/svg}line": OccSvgLine,
    "{http://www.w3.org/2000/svg}rect": OccSvgRect,
    "{http://www.w3.org/2000/svg}path": OccSvgPath,
    "{http://www.w3.org/2000/svg}polyline": OccSvgPolyline,
    "{http://www.w3.org/2000/svg}polygon": OccSvgPolygon,
    "{http://www.w3.org/2000/svg}g": OccSvgGroup,
    "{http://www.w3.org/2000/svg}svg": OccSvgDoc,
}


class OccSvg(OccShape, ProxySvg):
    #: Update the class reference
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_builder_a_p_i___make_wire.html"
    )

    #: Make wire
    shape = Instance(TopoDS_Shape)

    #: The document
    doc = Instance(OccSvgDoc)

    def create_shape(self):
        d = self.declaration
        if not d.source:
            return
        if os.path.exists(os.path.expanduser(d.source)):
            svg = etree.parse(os.path.expanduser(d.source)).getroot()
        else:
            svg = etree.fromstring(d.source)
        root = self.doc = OccSvgDoc(element=svg, svg=self)
        viewbox = svg.attrib.get("viewBox")
        x, y = (0, 0)
        sx, sy = (1, 1)
        if viewbox:
            x, y, iw, ih = map(parse_unit, viewbox.split())
            ow = parse_unit(svg.attrib.get("width", iw))
            oh = parse_unit(svg.attrib.get("height", ih))
            sx = ow / iw
            sy = oh / ih

        builder = BRep_Builder()
        shape = TopoDS_Compound()
        builder.MakeCompound(shape)
        for s in root.create_shape():
            builder.Add(shape, s)

        # Apply viewport scale
        t = gp_Trsf()
        t.SetValues(sx, 0, 0, x, 0, sy, 0, y, 0, 0, 1, 0)
        shape = BRepBuilderAPI_Transform(shape, t, True).Shape()

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
