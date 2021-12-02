"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
import os
from math import pi
from atom.api import Typed, Int, Tuple, List, set_default

from OCCT import Aspect, TCollection, NCollection, Graphic3d
from OCCT.BRep import BRep_Tool
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakePolygon, BRepBuilderAPI_Transform,
    BRepBuilderAPI_MakeVertex, BRepBuilderAPI_MakeWire
)
from OCCT.BRepOffsetAPI import BRepOffsetAPI_MiddlePath
from OCCT.BRepLib import BRepLib
from OCCT.Font import (
    Font_FontMgr, Font_BRepFont, Font_BRepTextBuilder, Font_FontAspect,
    Font_FA_Regular
)
from OCCT.GC import (
    GC_MakeSegment, GC_MakeArcOfCircle, GC_MakeArcOfEllipse, GC_MakeLine
)
from OCCT.gp import (
    gp_Dir, gp_Pnt, gp_Lin, gp_Pln, gp_Circ, gp_Elips, gp_Vec, gp_Trsf,
    gp_Ax3, gp_Ax2, gp
)
from OCCT.GeomAbs import (
    GeomAbs_C0, GeomAbs_C1, GeomAbs_C2, GeomAbs_C3, GeomAbs_CN
)
from OCCT.TopTools import TopTools_ListOfShape
from OCCT.TopoDS import (
    TopoDS, TopoDS_Shape, TopoDS_Edge, TopoDS_Wire, TopoDS_Vertex
)
from OCCT.GeomAPI import GeomAPI_PointsToBSpline, GeomAPI, GeomAPI_Interpolate
from OCCT.Geom import (
    Geom_BezierCurve, Geom_BSplineCurve, Geom_TrimmedCurve, Geom_Plane,
    Geom_Ellipse, Geom_Circle, Geom_Parabola, Geom_Hyperbola, Geom_Line,
    Geom_CartesianPoint
)
from OCCT.TColgp import (
    TColgp_Array1OfPnt, TColgp_Array1OfVec, TColgp_HArray1OfPnt
)
from OCCT.TColStd import (
    TColStd_Array1OfReal, TColStd_HArray1OfReal, TColStd_HArray1OfBoolean
)

from declaracad.occ.shape import (
    Shape, Direction, coerce_point, coerce_direction
)
from declaracad.occ.draw import (
    ProxyPlane, ProxyVertex, ProxyLine, ProxyCircle, ProxyEllipse,
    ProxyHyperbola, ProxyParabola, ProxyEdge, ProxyWire, ProxySegment,
    ProxyArc, ProxyPolyline, ProxyBSpline, ProxyBezier, ProxyTrimmedCurve,
    ProxyText, ProxyRectangle, ProxyMiddlePath
)
from .occ_shape import OccShape, OccDependentShape, Topology, coerce_axis
from .occ_svg import make_ellipse
from .utils import color_to_quantity_color

from declaracad.core.utils import log


#: Track registered fonts
FONT_MANAGER = Font_FontMgr.GetInstance_()
FONT_REGISTRY = set()
FONT_CACHE = {}


MARKERS = {
    'plus': Aspect.Aspect_TOM_PLUS,
    'point': Aspect.Aspect_TOM_POINT,
    'star': Aspect.Aspect_TOM_STAR,
    'cross': Aspect.Aspect_TOM_X,
    'circle': Aspect.Aspect_TOM_O,
    'point-in-circle': Aspect.Aspect_TOM_O_POINT,
    'star-in-circle': Aspect.Aspect_TOM_O_STAR,
    'plus-in-circle': Aspect.Aspect_TOM_O_PLUS,
    'cross-in-circle': Aspect.Aspect_TOM_O_X,
    'large-ring': Aspect.Aspect_TOM_RING1,
    'medium-ring': Aspect.Aspect_TOM_RING2,
    'small-ring': Aspect.Aspect_TOM_RING3,
    'ball': Aspect.Aspect_TOM_BALL,
    'dot': Aspect.Aspect_TOM_POINT,
}


LINE_TYPES = {
    'solid': Aspect.Aspect_TOL_SOLID,
    'dashed': Aspect.Aspect_TOL_DASH,
    'dotted': Aspect.Aspect_TOL_DOT,
    'dot_dash': Aspect.Aspect_TOL_DOTDASH,
}


CONTINUITY = {
    0: GeomAbs_C0,
    1: GeomAbs_C1,
    2: GeomAbs_C2,
    3: GeomAbs_C3,
    None: GeomAbs_CN,
}


class OccPlane(OccShape, ProxyPlane):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___pnt.html')

    curve = Typed(Geom_Plane)

    def create_shape(self):
        d = self.declaration
        pln = gp_Pln(d.position.proxy, d.direction.proxy)

        curve = self.curve = Geom_Plane(pln)
        if d.bounds:
            u, v = d.bounds
            face = BRepBuilderAPI_MakeFace(pln, u.x, v.x, u.y, v.y)
        else:
            face = BRepBuilderAPI_MakeFace(pln)

        self.shape = face.Face()

    def set_bounds(self, bounds):
        self.create_shape()


class OccVertex(OccShape, ProxyVertex):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_vertex.html')

    def create_shape(self):
        pt = self.declaration.position.proxy
        self.shape = BRepBuilderAPI_MakeVertex(pt).Vertex()

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        marker = MARKERS.get(d.marker)
        if marker:
            ais_shape.Attributes().PointAspect().SetTypeOfMarker(marker)
        return ais_shape


class OccEdge(OccShape, ProxyEdge):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_edge.html')

    curve = Typed(Geom_TrimmedCurve)

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        if d.line_style != 'solid':
            type_of_line = LINE_TYPES[d.line_style]
            if d.as_wire:
                ais_shape.Attributes().WireAspect().SetTypeOfLine(type_of_line)
            else:
                ais_shape.Attributes().LineAspect().SetTypeOfLine(type_of_line)
        if d.line_width > 0:
            ais_shape.SetWidth(d.line_width)
        return ais_shape

    def make_edge(self, *args):
        d = self.declaration
        if d.surface:
            # Convert the curve to 2d
            args = list(args)
            pln = gp_Pln(d.position.proxy, d.direction.proxy)
            args[0] = GeomAPI.To2d_(args[0], pln)
            args.insert(1,  BRep_Tool.Surface_(d.surface))
        edge = BRepBuilderAPI_MakeEdge(*args).Edge()
        if d.as_wire:
            return BRepBuilderAPI_MakeWire(edge).Wire()
        return edge

    def get_value_at(self, t, derivative=0):
        if self.curve is None:
            self.create_shape()
        return Topology.get_value_at(self.curve, t, derivative)

    def set_surface(self, surface):
        self.create_shape()

    def set_as_wire(self, enabled):
        self.create_shape()


class OccLine(OccEdge, ProxyLine):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___lin.html')

    curve = Typed(Geom_Line)

    def get_transformed_points(self, points=None):
        d = self.declaration
        t = self.get_transform()
        return [p.proxy.Transformed(t) for p in points or d.points]

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        if n == 2:
            curve = GC_MakeLine(*self.get_transformed_points()).Value()
        elif n == 1:
            lin = gp_Lin(d.position.proxy, gp_Vec(d.direction.proxy))
            offset_point = self.get_transformed_points()
            curve = GC_MakeLine(lin, offset_point).Value()
        else:
            axis = coerce_axis(d.axis)
            curve = GC_MakeLine(axis.Axis()).Value()
        self.curve = curve
        self.shape = self.make_edge(curve)

    def set_points(self, points):
        self.create_shape()


class OccSegment(OccLine, ProxySegment):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_g_c___make_segment.html')

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        d = self.declaration
        points = self.get_transformed_points()
        if len(points) != 2:
            raise ValueError("A segment requires exactly two points")
        segment = self.curve = GC_MakeSegment(points[0], points[1]).Value()
        self.shape = self.make_edge(segment)


class OccArc(OccLine, ProxyArc):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_g_c___make_arc_of_circle.html')

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        try:
            if d.solve:
               arc = self.create_arc_from_solver(**d.solve)
            elif d.radius:
                points = [p.proxy for p in d.points]  # Do not trasnform these
                #if d.radius2:
                #    g = gp_Elips(coerce_axis(d.axis), d.radius, d.radius2)
                #    factory = GC_MakeArcOfEllipse
                #else:
                v = d.direction.proxy
                # TODO: This technially isn't correct because the z axis could
                # already be flipped
                if d.clockwise:
                    v = v.Reversed()
                axis = gp_Ax2(d.position.proxy, v)
                c = gp_Circ(axis, d.radius)

                if n == 2:
                    start, end = points
                    if start.IsEqual(end, d.tolerance):
                        # Full circle
                        center = d.position.proxy
                        start_direction = gp_Dir(gp_Vec(center, start))
                        start_angle = axis.XDirection().Angle(start_direction)
                        angle = start_angle + 2 * pi
                        arc = GC_MakeArcOfCircle(c, start, angle, True).Value()
                    else:
                        arc = GC_MakeArcOfCircle(c, start, end, True).Value()
                elif n == 1:
                    arc = GC_MakeArcOfCircle(c, points[0], d.alpha1, True).Value()
                else:
                    arc = GC_MakeArcOfCircle(c, d.alpha1, d.alpha2, True).Value()
            #elif n == 2:
            #    # TODO: This doesn't work
            #    points = self.get_transformed_points()
            #    arc = GC_MakeArcOfEllipse(points[0], points[1]).Value()
            elif n == 3:
                if isinstance(d.points[1], Direction):
                    points = self.get_transformed_points([d.points[0], d.points[2]])
                    points.insert(1, gp_Vec(d.points[1].proxy))
                else:
                    points = self.get_transformed_points()
                arc = GC_MakeArcOfCircle(points[0], points[1], points[2]).Value()
            else:
                raise ValueError("Could not create an Arc with the given children "
                                "and parameters. Must be given one of:\n\t"
                                "- two or three points\n\t"
                                "- radius and 2 points\n\t"
                                "- radius, alpha1 and one point\n\t"
                                "- radius, alpha1 and alpha2")
        except RuntimeError as e:
            raise RuntimeError(f"Could not create arc {d}: {e}")

        if d.reverse:
            arc.Reverse()
        self.curve = arc
        self.shape = self.make_edge(arc)

    def create_arc_from_solver(self, **params):
        """ Create an arc by solving the given parameters.

        """
        d = self.declaration
        raise NotImplementedError("TODO")

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_alpha1(self, a):
        self.create_shape()

    def set_alpha2(self, a):
        self.create_shape()

    def set_reverse(self, reverse):
        self.create_shape()

    def set_clockwise(self, clockwise):
        self.create_shape()


class OccCircle(OccEdge, ProxyCircle):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___circ.html')

    curve = Typed(Geom_Circle)

    def create_shape(self):
        d = self.declaration
        curve = self.curve = Geom_Circle(coerce_axis(d.axis), d.radius)
        self.shape = self.make_edge(curve)

    def set_radius(self, r):
        self.create_shape()


class OccEllipse(OccEdge, ProxyEllipse):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___elips.html')

    curve = Typed(Geom_Ellipse)

    def create_shape(self):
        d = self.declaration
        major = max(d.major_radius, d.minor_radius)
        minor = min(d.major_radius, d.minor_radius)
        curve = self.curve = Geom_Ellipse(coerce_axis(d.axis), major, minor)
        self.shape = self.make_edge(curve)

    def set_major_radius(self, r):
        self.create_shape()

    def set_minor_radius(self, r):
        self.create_shape()


class OccHyperbola(OccEdge, ProxyHyperbola):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___hypr.html')

    curve = Typed(Geom_Hyperbola)

    def create_shape(self):
        d = self.declaration
        major = max(d.major_radius, d.minor_radius)
        minor = min(d.major_radius, d.minor_radius)
        curve = self.curve = Geom_Hyperbola(coerce_axis(d.axis), major, minor)
        self.shape = self.make_edge(curve)

    def set_major_radius(self, r):
        self.create_shape()

    def set_minor_radius(self, r):
        self.create_shape()


class OccParabola(OccEdge, ProxyParabola):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___parab.html')

    curve = Typed(Geom_Parabola)

    def create_shape(self):
        d = self.declaration
        curve = self.curve = Geom_Parabola(coerce_axis(d.axis), d.focal_length)
        self.shape = self.make_edge(curve)

    def set_focal_length(self, l):
        self.create_shape()


class OccBSpline(OccLine, ProxyBSpline):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_geom___b_spline_curve.html')

    curve = Typed(Geom_BSplineCurve)

    def create_shape(self):
        d = self.declaration
        if not d.points:
            raise ValueError("Must have at least two points")

        # Poles and weights
        points = self.get_transformed_points()

        if d.interpolate or d.tangents or d.periodic:
            pts = TColgp_HArray1OfPnt(1, len(points))
            for i, p in enumerate(points):
                pts.SetValue(i+1, p)

            if d.parameters:
                params = TColStd_HArray1OfReal(1, len(points))
                for i, p in enumerate(d.parameters):
                    params.SetValue(i+1, p)
                f = GeomAPI_Interpolate(pts, params, d.periodic, d.tolerance)
            else:
                f = GeomAPI_Interpolate(pts, d.periodic, d.tolerance)

            if d.tangents:
                n = len(d.tangents)
                if n == 2:
                    start, end = d.tangents
                    f.Load(gp_Vec(*start), gp_Vec(*end))
                else:
                    tangents = TColgp_Array1OfVec(1, n)
                    flags = TColStd_HArray1OfBoolean(1, n)
                    for i, p in enumerate(d.parameters):
                        tangents.SetValue(i+1, p)
                        flags.SetValue(i+1, True)
                    f.Load(tangents, flags)

            f.Perform()
        else:
            cty = CONTINUITY[d.continuity]
            pts = TColgp_Array1OfPnt(1, len(points))
            for i, p in enumerate(points):
                pts.SetValue(i+1, p)

            if d.parameters:
                params = TColStd_Array1OfReal(1, len(points))
                for i, p in enumerate(d.parameters):
                    params.SetValue(i+1, p)
                f = GeomAPI_PointsToBSpline(
                    pts, params, d.deg_min, d.deg_max, cty, d.tolerance)
            else:
                f = GeomAPI_PointsToBSpline(
                    pts, d.deg_min, d.deg_max, cty, d.tolerance)
        curve = self.curve = f.Curve()
        self.shape = self.make_edge(curve)


class OccBezier(OccLine, ProxyBezier):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_geom___bezier_curve.html')

    curve = Typed(Geom_BezierCurve)

    def create_shape(self):
        d = self.declaration
        n = len(d.points)
        if n < 2:
            raise ValueError("A bezier must have at least 2 points!")

        points = self.get_transformed_points()
        pts = TColgp_Array1OfPnt(1, n)
        set_value = pts.SetValue

        # TODO: Support weights
        for i, p in enumerate(points):
            set_value(i+1, p)

        curve = self.curve = Geom_BezierCurve(pts)
        self.shape = self.make_edge(curve)


class OccText(OccShape, ProxyText):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_topo_d_s___shape.html')

    builder = Typed(Font_BRepTextBuilder, ())

    font = Typed(Font_BRepFont)

    def update_font(self, change=None):
        self.font = self._default_font()

    def _default_font(self):
        d = self.declaration
        font_family = d.font
        if font_family and os.path.exists(font_family) \
                and font_family not in FONT_REGISTRY:
            FONT_MANAGER.RegisterFont(font_family, True)
            FONT_REGISTRY.add(font_family)

        attr = "Font_FA_{}".format(d.style.title().replace("-", ""))
        font_style = getattr(Font_FontAspect, attr, Font_FA_Regular)

        # Fonts are cached by OpenCASCADE so we also cache the here or
        # each time the font instance is released by python it get's lost
        key = (font_family, d.style, d.size)
        font = FONT_CACHE.get(key)
        if font is None:
            font_name = TCollection.TCollection_AsciiString(font_family)
            font = Font_BRepFont()
            assert font.FindAndInit(font_name, font_style, float(d.size))
            FONT_CACHE[key] = font
        return font

    def create_shape(self):
        """ Create the shape by loading it from the given path. """
        d = self.declaration
        font = self.font
        axis = gp_Ax3(coerce_axis(d.axis))
        attr = 'Graphic3d_HTA_{}'.format(d.horizontal_alignment.upper())
        halign = getattr(Graphic3d, attr)
        attr = 'Graphic3d_VTA_{}'.format(d.vertical_alignment .upper())
        valign = getattr(Graphic3d, attr)
        text = NCollection.NCollection_String(d.text.encode("utf-8"))
        self.shape = self.builder.Perform(self.font, text, axis, halign, valign)

    def set_text(self, text):
        self.create_shape()

    def set_font(self, font):
        self.update_font()
        self.create_shape()

    def set_size(self, size):
        self.update_font()
        self.create_shape()

    def set_style(self, style):
        self.update_font()
        self.create_shape()

    def set_composite(self, composite):
        self.create_shape()

    def set_vertical_alignment(self, alignment):
        self.create_shape()

    def set_horizontal_alignment(self, alignment):
        self.create_shape()


class OccTrimmedCurve(OccEdge, ProxyTrimmedCurve):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_geom___trimmed_curve.html')

    curve = Typed(Geom_TrimmedCurve)

    def create_shape(self):
        pass

    def init_layout(self):
        self.update_shape()
        for child in self.children():
            if not isinstance(child, OccShape):
                continue
            child.observe('shape', self.update_shape)

    def update_shape(self, change=None):
        d = self.declaration
        child = self.get_first_child()
        if hasattr(child, 'curve'):
            curve = child.curve
        else:
            curve = BRep_Tool.Curve_(child.shape, 0, 1)[0]
        trimmed_curve = self.curve = Geom_TrimmedCurve(curve, d.u, d.v)
        self.shape = self.make_edge(trimmed_curve)

    def set_u(self, u):
        self.update_shape()

    def set_v(self, v):
        self.update_shape()


class OccWire(OccDependentShape, ProxyWire):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_wire.html')

    curve = Typed(BRepAdaptor_CompCurve)

    def _default_ais_shape(self):
        d = self.declaration
        ais_shape = super()._default_ais_shape()
        if d.line_style != 'solid':
            type_of_line = LINE_TYPES[d.line_style]
            ais_shape.Attributes().WireAspect().SetTypeOfLine(type_of_line)
        if d.line_width > 0:
            ais_shape.SetWidth(d.line_width)
        return ais_shape

    def create_shape(self):
        pass

    def update_shape(self, change=None):
        d = self.declaration
        edges = TopTools_ListOfShape()
        wires = []
        for c in self.children():
            if not isinstance(c, OccShape):
                continue
            if c.shape is None:
                raise ValueError("Cannot build wire from empty shape: %s" % c)
            self.extract_edges(c, edges)
        else:
            for edge in d.edges:
                if isinstance(edge, TopoDS_Edge):
                    edges.Append(edge)
                else:
                    wires.append(edge)

        builder = BRepBuilderAPI_MakeWire()
        builder.Add(edges)
        for w in wires:
            builder.Add(w)
        if not builder.IsDone():
            log.warning('Edges must be connected %s' % d)
        try:
            wire = builder.Wire()
        except RuntimeError as e:
            msg = f'Error creating wire for {d}: {e}'
            raise RuntimeError(msg)
        if d.reverse:
            wire.Reverse()
        self.curve = BRepAdaptor_CompCurve(wire)
        self.shape = wire

    def extract_edges(self, child, edges):
        d = child.declaration
        if isinstance(child.shape, list):
            for c in child.children():
                if not isinstance(c, OccShape):
                    continue
                self.extract_edges(c, edges)
        else:
            for edge in d.topology.edges:
                if getattr(d, 'surface', None):
                    BRepLib.BuildCurves3d_(edge)
                edges.Append(edge)

    def get_value_at(self, t, derivative=0):
        if self.curve is None:
            self.update_shape()
        return Topology.get_value_at(self.curve, t, derivative)


class OccPolyline(OccWire, ProxyPolyline):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_builder_a_p_i___make_polygon.html')

    curve = Typed(BRepAdaptor_CompCurve)

    def create_shape(self):
        d = self.declaration
        t = self.get_transform()
        shape = BRepBuilderAPI_MakePolygon()
        for p in d.points:
            shape.Add(p.proxy.Transformed(t))
        if d.closed:
            shape.Close()
        curve = self.curve = BRepAdaptor_CompCurve(shape.Wire())
        self.shape = curve.Wire()

    def init_layout(self):
        # This does not depened on children
        pass

    def update_shape(self, change=None):
        self.create_shape()

    def set_closed(self, closed):
        self.create_shape()


class OccRectangle(OccWire, ProxyRectangle):
    curve = Typed(BRepAdaptor_CompCurve)

    def create_shape(self):
        d = self.declaration
        t = self.get_transform()
        w, h = d.width, d.height
        if d.rx or d.ry:
            rx, ry = d.rx, d.ry
            if not ry:
                ry = rx
            elif not rx:
                rx = ry

            # Clamp to the valid range
            rx = min(w/2, rx)
            ry = min(h/2, ry)

            # Bottom
            p1 = gp_Pnt(0+rx, 0, 0)
            p2 = gp_Pnt(0+w-rx, 0, 0)

            # Right
            p3 = gp_Pnt(w, ry, 0)
            p4 = gp_Pnt(w, h-ry, 0)

            # Top
            p5 = gp_Pnt(w-rx, h, 0)
            p6 = gp_Pnt(rx, h, 0)

            # Left
            p7 = gp_Pnt(0, h-ry, 0)
            p8 = gp_Pnt(0, ry, 0)

            shape = BRepBuilderAPI_MakeWire()

            e = d.tolerance

            # Bottom
            if not p1.IsEqual(p2, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p1, p2).Edge())

            # Arc bottom right
            c = make_ellipse((w-rx, ry, 0), rx, ry)
            shape.Add(BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p2, p3, False).Value()).Edge())

            # Right
            if not p3.IsEqual(p4, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p3, p4).Edge())

            # Arc top right
            c.SetLocation(gp_Pnt(w-rx, h-ry, 0))
            shape.Add(BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p4, p5, False).Value()).Edge())

            # Top
            if not p5.IsEqual(p6, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p5, p6).Edge())

            # Arc top left
            c.SetLocation(gp_Pnt(rx, h-ry, 0))
            shape.Add(BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p6, p7, False).Value()).Edge())

            # Left
            if not p7.IsEqual(p8, e):
                shape.Add(BRepBuilderAPI_MakeEdge(p7, p8).Edge())

            # Arc bottom left
            c.SetLocation(gp_Pnt(rx, ry, 0))
            shape.Add(BRepBuilderAPI_MakeEdge(
                GC_MakeArcOfEllipse(c, p8, p1, False).Value()).Edge())

            shape = shape.Wire()
            shape.Closed(True)
        else:
            shape = BRepBuilderAPI_MakePolygon(
                gp_Pnt(0, 0, 0), gp_Pnt(w, 0, 0),
                gp_Pnt(w, h, 0), gp_Pnt(0, h, 0), True).Wire()
        wire = TopoDS.Wire_(BRepBuilderAPI_Transform(shape, t, False).Shape())
        self.curve = BRepAdaptor_CompCurve(wire)
        self.shape = wire

    def update_shape(self, change=None):
        self.create_shape()

    def init_layout(self):
        # This does not depened on children
        pass


class OccMiddlePath(OccWire, ProxyMiddlePath):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___middle_path.html')

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
