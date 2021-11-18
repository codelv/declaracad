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
from atom.api import Atom, List, Instance, set_default
from lxml import etree
from math import radians, sqrt, tan, atan, atan2, cos, acos, sin, pi

from OCCT.BRep import BRep_Builder
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform
)
#from OCCT.BRepLib import breplib_BuildCurves3d
from OCCT.GC import GC_MakeArcOfEllipse
from OCCT.Geom import Geom_BezierCurve, Geom_BSplineCurve
from OCCT.gp import (
    gp_Dir, gp_Pnt, gp_Circ, gp_Elips, gp_Ax1, gp_Ax2, gp_Trsf, gp_Ax3, gp_Vec
)
from OCCT.TColgp import TColgp_Array1OfPnt
from OCCT.TopoDS import TopoDS_Shape, TopoDS_Compound#, topods


from .occ_shape import OccShape
from ..draw import ProxySvg

from declaracad.core.utils import log

Z_DIR = gp_Dir(0, 0, 1)
NEG_Z_DIR = gp_Dir(0, 0, -1)
Z_AXIS = gp_Ax1(gp_Pnt(0, 0, 0), Z_DIR)

UNITS = {
    'in': 90.0, 'pt': 1.25, 'px': 1, 'mm': 3.5433070866,
    'cm': 35.433070866, 'm': 3543.3070866,
    'km': 3543307.0866, 'pc': 15.0, 'yd': 3240, 'ft': 1080
}

# From  simplepath.py's parsePath by Aaron Spike, aaron@ekips.org
PATHDEFS = {
    'M': ['L', 2, [float, float], ['x', 'y']],
    'L': ['L', 2, [float, float], ['x', 'y']],
    'H': ['H', 1, [float], ['x']],
    'V': ['V', 1, [float], ['y']],
    'C': ['C', 6, [float, float, float, float, float, float],
                    ['x', 'y', 'x', 'y', 'x', 'y']],
    'S': ['S', 4, [float, float, float, float], ['x', 'y', 'x', 'y']],
    'Q': ['Q', 4, [float, float, float, float], ['x', 'y', 'x', 'y']],
    'T': ['T', 2, [float, float], ['x', 'y']],
    'A': ['A', 7, [float, float, float, int, int, float, float],
                    ['r', 'r', 'a', 'a', 's', 'x', 'y']],
    'Z': ['L', 0, [], []]
}


def parse_unit(value):
    """ Returns userunits given a string representation of units
    in another system
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return value

    unit = re.compile('(%s)$' % '|'.join(UNITS.keys()))
    param = re.compile(
        r'(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)')

    p = param.match(value)
    u = unit.search(value)
    if p:
        retval = float(p.string[p.start():p.end()])
    else:
        retval = 0.0
    if u:
        try:
            return retval * UNITS[u.string[u.start():u.end()]]
        except KeyError:
            pass
    return retval


def make_ellipse(p, rx, ry, rotate=0, direction=Z_DIR):
    """ gp_Elips doesn't allow minor > major so swap and rotate instead if
    that's the case.
    """
    c = gp_Pnt(*p)
    if ry > rx:
        rx, ry = ry, rx # Swap
        rotate += pi/2
        # This only works when rotate == 0
    ellipse = gp_Elips(gp_Ax2(c, direction), rx, ry)
    ellipse.Rotate(gp_Ax1(c, direction), rotate)
    return ellipse


def compute_arc_center(x1, y1, rx, ry, phi, large_arc_flag, sweep_flag,
                       x2, y2):
    """ Compute center point of an arc based SVG parameters given.
    Thanks to Arnout Engelen's work in Inkcut.

    Notes
    -----
    See https://www.w3.org/TR/SVG/implnote.html F.6.6

    """
    rx = abs(rx)
    ry = abs(ry)

    # https://www.w3.org/TR/SVG/implnote.html F.6.5
    x1prime = cos(phi)*(x1 - x2)/2 + sin(phi)*(y1 - y2)/2
    y1prime = -sin(phi)*(x1 - x2)/2 + cos(phi)*(y1 - y2)/2

    # https://www.w3.org/TR/SVG/implnote.html F.6.6
    lamb = (x1prime*x1prime)/(rx*rx) + (y1prime*y1prime)/(ry*ry)
    if lamb >= 1:
        ry = sqrt(lamb)*ry
        rx = sqrt(lamb)*rx

    # Back to https://www.w3.org/TR/SVG/implnote.html F.6.5
    radicand = (rx*rx*ry*ry - rx*rx*y1prime*y1prime - ry*ry*x1prime*x1prime)
    radicand /= (rx*rx*y1prime*y1prime + ry*ry*x1prime*x1prime)

    if radicand < 0:
        radicand = 0

    factor = (-1 if large_arc_flag == sweep_flag else 1)*sqrt(radicand)

    cxprime = factor*rx*y1prime/ry
    cyprime = -factor*ry*x1prime/rx

    cx = cxprime*cos(phi) - cyprime*sin(phi) + (x1 + x2)/2
    cy = cxprime*sin(phi) + cyprime*cos(phi) + (y1 + y2)/2
    #if phi == 0:
        #start_theta = -atan2((y1 - cy) * rx, (x1 - cx) * ry)

        #start_phi = -atan2(y1 - cy, x1 - cx)
        #end_phi = -atan2(y2 - cy, x2 - cx)

        #sweep_length = end_phi - start_phi

        #if sweep_length < 0 and not sweep_flag:
            #sweep_length += 2 * pi
        #elif sweep_length > 0 and sweep_flag:
            #sweep_length -= 2 * pi

        #self.arcTo(cx - rx, cy - ry, rx * 2, ry * 2,
            #start_theta * 360 / 2 / pi, sweep_length * 360 / 2 / pi)
    return (cx, cy, rx, ry)


class OccSvgNode(Atom):
    #: Element
    element = Instance(etree._Element)

    def create_shape(self):
        """ Create and return the shape for the given svg node.
        """
        raise NotImplementedError


class OccSvgEllipse(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        cx = parse_unit(attrs.get('cx', 0))
        cy = parse_unit(attrs.get('cy', 0))
        rx = parse_unit(attrs.get('rx', 0))
        ry = parse_unit(attrs.get('ry', 0))
        ellipse = make_ellipse((cx, cy, 0), rx, ry)
        return BRepBuilderAPI_MakeEdge(ellipse).Edge()


class OccSvgCircle(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        cx = parse_unit(attrs.get('cx', 0))
        cy = parse_unit(attrs.get('cy', 0))
        r = parse_unit(attrs.get('r', 0))
        circle = gp_Circ(gp_Ax2(gp_Pnt(cx, cy, 0), Z_DIR), r)
        return BRepBuilderAPI_MakeEdge(circle).Edge()


class OccSvgLine(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        x1 = parse_unit(attrs.get('x1', 0))
        y1 = parse_unit(attrs.get('y1', 0))
        x2 = parse_unit(attrs.get('x2', 0))
        y2 = parse_unit(attrs.get('y2', 0))
        return BRepBuilderAPI_MakeEdge(gp_Pnt(x1, y1, 0),
                                       gp_Pnt(x2, y2, 0)).Edge()


class OccSvgRect(OccSvgNode):
    def create_shape(self):
        attrs = self.element.attrib
        x = parse_unit(attrs.get('x', 0))
        y = parse_unit(attrs.get('y', 0))
        w = parse_unit(attrs.get('width', 0))
        h = parse_unit(attrs.get('height', 0))
        rx = parse_unit(attrs.get('rx', 0))
        ry = parse_unit(attrs.get('ry', 0))
        if rx == ry == 0:
            shape = BRepBuilderAPI_MakePolygon(
                gp_Pnt(x, y, 0), gp_Pnt(x+w, y, 0),
                gp_Pnt(x+w, y+h, 0), gp_Pnt(x, y+h, 0),
                True
            )
            return shape.Wire()
        elif rx == 0:
            rx = ry
        elif ry == 0:
            ry = rx

        # Build the rect
        shape = BRepBuilderAPI_MakeWire()

        # Bottom
        p1 = gp_Pnt(x+rx, y, 0)
        p2 = gp_Pnt(x+w-rx, y, 0)

        # Right
        p3 = gp_Pnt(x+w, y+ry, 0)
        p4 = gp_Pnt(x+w, y+h-ry, 0)

        # Top
        p5 = gp_Pnt(x+w-rx, y+h, 0)
        p6 = gp_Pnt(x+rx, y+h, 0)

        # Left
        p7 = gp_Pnt(x, y+h-ry, 0)
        p8 = gp_Pnt(x, y+ry, 0)

        # Bottom
        shape.Add(BRepBuilderAPI_MakeEdge(p1, p2).Edge())

        # Arc bottom right
        c = make_ellipse((x+w-rx, y+ry, 0), rx, ry)
        shape.Add(BRepBuilderAPI_MakeEdge(
            GC_MakeArcOfEllipse(c, p2, p3, False).Value()).Edge())

        # Right
        shape.Add(BRepBuilderAPI_MakeEdge(p3, p4).Edge())

        # Arc top right
        c.SetLocation(gp_Pnt(x+w-rx, y+h-ry, 0))
        shape.Add(BRepBuilderAPI_MakeEdge(
            GC_MakeArcOfEllipse(c, p4, p5, False).Value()).Edge())

        # Top
        shape.Add(BRepBuilderAPI_MakeEdge(p5, p6).Edge())

        # Arc top left
        c.SetLocation(gp_Pnt(x+rx, y+h-ry, 0))
        shape.Add(BRepBuilderAPI_MakeEdge(
            GC_MakeArcOfEllipse(c, p6, p7, False).Value()).Edge())

        # Left
        shape.Add(BRepBuilderAPI_MakeEdge(p7, p8).Edge())

        # Arc bottom left
        c.SetLocation(gp_Pnt(x+rx, y+ry, 0))
        shape.Add(BRepBuilderAPI_MakeEdge(
            GC_MakeArcOfEllipse(c, p8, p1, False).Value()).Edge())

        wire = shape.Wire()
        wire.Closed(True)
        return wire


class OccSvgPath(OccSvgNode):

    def path_lexer(self, d):
        """
        From  simplepath.py's parsePath by Aaron Spike, aaron@ekips.org

        returns and iterator that breaks path data
        identifies cmd and parameter tokens
        """
        offset = 0
        length = len(d)
        delim = re.compile(r'[ \t\r\n,]+')
        cmd = re.compile(r'[MLHVCSQTAZmlhvcsqtaz]')
        parameter = re.compile(
            r'(([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?)')
        while True:
            m = delim.match(d, offset)
            if m:
                offset = m.end()
            if offset >= length:
                break
            m = cmd.match(d, offset)
            if m:
                yield [d[offset:m.end()], True]
                offset = m.end()
                continue
            m = parameter.match(d, offset)
            if m:
                yield [d[offset:m.end()], False]
                offset = m.end()
                continue
            raise ValueError('Invalid path data at %s!' % offset)

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
        last_cmd = ''

        while True:
            try:
                token, is_cmd = next(lexer)
            except StopIteration:
                break
            params = []
            need_param = True
            if is_cmd:
                if not last_cmd and token.upper() != 'M':
                    raise ValueError('Invalid path, must begin with moveto ('
                                     'M or m), given %s.' % last_cmd)
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
                    raise ValueError('Invalid path, no initial cmd.')
            num_params = PATHDEFS[cmd.upper()][1]
            while num_params > 0:
                if need_param:
                    try:
                        token, is_cmd = next(lexer)
                        if is_cmd:
                            raise ValueError('Invalid number of parameters '
                                             'for %s' % (cmd, ))
                    except StopIteration:
                        raise Exception('Unexpected end of path')
                cast = PATHDEFS[cmd.upper()][2][-num_params]
                param = cast(token)
                if cmd.islower():
                    if PATHDEFS[cmd.upper()][3][-num_params] == 'x':
                        param += pen[0]
                    elif PATHDEFS[cmd.upper()][3][-num_params] == 'y':
                        param += pen[1]
                params.append(param)
                need_param = True
                num_params -= 1
            # segment is now absolute so
            output_cmd = cmd.upper()

            # Flesh out shortcut notation
            if output_cmd in ('H', 'V'):
                if output_cmd == 'H':
                    params.append(pen[1])
                if output_cmd == 'V':
                    params.insert(0, pen[0])
                output_cmd = 'L'
            if output_cmd in ('S', 'T'):
                params.insert(0, pen[1]+(pen[1]-last_control[1]))
                params.insert(0, pen[0]+(pen[0]-last_control[0]))
                if output_cmd == 'S':
                    output_cmd = 'C'
                if output_cmd == 'T':
                    output_cmd = 'Q'

            # current values become "last" values
            if output_cmd == 'M':
                sub_path_start = tuple(params[0:2])
                pen = sub_path_start
            if output_cmd == 'Z':
                pen = sub_path_start
            else:
                pen = tuple(params[-2:])

            if output_cmd in ('Q', 'C'):
                last_control = tuple(params[-4:-2])
            else:
                last_control = pen

            last_cmd = cmd

            yield (output_cmd, params)

    def create_shape(self):
        data = self.element.attrib.get('d')
        shapes = []
        path = None
        for cmd, params in self.parse_path(data):
            if cmd == 'M':
                if path is not None:
                    shapes.append(path.Wire())
                path = BRepBuilderAPI_MakeWire()
                last_pnt = gp_Pnt(params[0], params[1], 0)
                start_pnt = last_pnt
            elif cmd in ['L', 'H', 'V']:
                pnt = gp_Pnt(params[0], params[1], 0)
                path.Add(BRepBuilderAPI_MakeEdge(last_pnt, pnt).Edge())
                last_pnt = pnt
            elif cmd == 'Q':
                # Quadratic Bezier
                pts = TColgp_Array1OfPnt(1, 3)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                last_pnt = gp_Pnt(params[2], params[3], 0)
                pts.SetValue(3, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd == 'C':
                # Cubic Bezier
                pts = TColgp_Array1OfPnt(1, 4)
                pts.SetValue(1, last_pnt)
                pts.SetValue(2, gp_Pnt(params[0], params[1], 0))
                pts.SetValue(3, gp_Pnt(params[2], params[3], 0))
                last_pnt = gp_Pnt(params[4], params[5], 0)
                pts.SetValue(4, last_pnt)
                curve = Geom_BezierCurve(pts)
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
            elif cmd == 'A':
                # Warning: Play at your own risk!
                x1, y1 = last_pnt.X(), last_pnt.Y()
                rx, ry, phi, large_arc_flag, sweep_flag, x2, y2 = params
                phi = radians(phi)
                pnt = gp_Pnt(x2, y2, 0)
                cx, cy, rx, ry = compute_arc_center(
                    x1, y1, rx, ry, phi, large_arc_flag, sweep_flag, x2, y2)
                z_dir = Z_DIR if sweep_flag else NEG_Z_DIR  # sweep_flag
                c = make_ellipse((cx, cy, 0), rx, ry, phi, z_dir)
                curve = GC_MakeArcOfEllipse(c, last_pnt, pnt, True).Value()
                path.Add(BRepBuilderAPI_MakeEdge(curve).Edge())
                last_pnt = pnt
            elif cmd == 'Z':
                if not last_pnt.IsEqual(start_pnt, 10e-6):
                    edge = BRepBuilderAPI_MakeEdge(last_pnt, start_pnt).Edge()
                    path.Add(edge)
                shapes.append(path.Wire())
                path = None  # Close path
                last_pnt = start_pnt
        if path is not None:
            shapes.append(path.Wire())
        return shapes


class OccSvgPolyline(OccSvgNode):
    def create_shape(self):
        shape = BRepBuilderAPI_MakePolygon()
        for m in re.finditer(r'(\-?\d+\.?\d*),(\-?\d+\.?\d*)\s+',
                             self.element.attrib.get('points', '')):
            x, y = map(float, m.groups())
            shape.Add(gp_Pnt(x, y, 0))
        return shape.Wire()


class OccSvgPolygon(OccSvgNode):
    def create_shape(self):
        shape = BRepBuilderAPI_MakePolygon()
        for m in re.finditer(r'(\-?\d+\.?\d*),(\-?\d+\.?\d*)\s+',
                             self.element.attrib.get('points', '')):
            x, y = map(float, m.groups())
            shape.Add(gp_Pnt(x, y, 0))
        shape.Close()
        return BRepBuilderAPI_MakeFace(shape.Wire()).Shape()


class OccSvgGroup(OccSvgNode):
    def create_shape(self):
        shapes = []
        for e in self.element:
            tag = e.tag
            if "{http://www.w3.org/2000/svg}" not in tag:
                tag = "{http://www.w3.org/2000/svg}" + tag
            OccNode = SVG_NODES.get(tag)
            if OccNode is None:
                warnings.warn(
                    "SVG tag {} is not yet supported.".format(e.tag))
                continue
            node = OccNode(element=e)
            shape = node.create_shape()
            if isinstance(shape, list):
                shapes.extend(shape)
            else:
                shapes.append(shape)
        return shapes



class OccSvgDoc(OccSvgGroup):
    """ TODO: Handle transforms """



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
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_wire.html')

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
        node = self.doc = OccSvgDoc(element=svg)
        viewbox = svg.attrib.get('viewBox')
        x, y = (0, 0)
        sx, sy = (1, 1)
        if viewbox:
            ow = parse_unit(svg.attrib.get('width'))
            oh = parse_unit(svg.attrib.get('height'))
            x, y, iw, ih = map(parse_unit, viewbox.split())
            sx = ow/iw
            sy = oh/ih

        builder = BRep_Builder()
        shape = TopoDS_Compound()
        builder.MakeCompound(shape)

        shapes = node.create_shape()
        for s in shapes:
            builder.Add(shape, s)

        bbox = self.get_bounding_box(shape)

        # Move to position and align along direction axis
        t = self.get_transform()
        if d.mirror:
            m = gp_Trsf()
            m.SetMirror(gp_Ax2(gp_Pnt(*bbox.center), gp_Dir(0, 1, 0)))
            t.Multiply(m)

        # Apply viewport scale
        s = gp_Trsf()
        s.SetValues(sx, 0, 0, x,
                    0, sy, 0, y,
                    0, 0, 1, 0)
        t.Multiply(s)

        self.shape = BRepBuilderAPI_Transform(shape, t, False).Shape()

    def set_source(self, source):
        self.create_shape()

    def set_mirror(self, mirror):
        self.create_shape()
