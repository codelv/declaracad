"""
Copyright (c) 2024, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os

import enaml
from math import pi, degrees
from atom.api import Bool, Float
from lxml import etree
from OCCT.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCCT.BRepAdaptor import BRepAdaptor_Curve
from OCCT.Geom import Geom_Circle, Geom_Ellipse, Geom_BezierCurve
from OCCT.Adaptor3d import Adaptor3d_Curve
from OCCT.GeomAdaptor import GeomAdaptor_Curve
from OCCT.GeomConvert import GeomConvert_BSplineCurveToBezierCurve
from OCCT.GCPnts import GCPnts_AbscissaPoint
from OCCT.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCCT.HLRAlgo import HLRAlgo_Projector
from OCCT.TopoDS import TopoDS_Wire, TopoDS_Edge

from declaracad.occ.api import Shape, Topology, Point
from declaracad.viewer.plugin import ModelExporter
from declaracad.occ.impl.occ_shape import AX


def circle_to_path(curve: Adaptor3d_Curve) -> str:
    """Convert a circular arc to svg path data. It must be in the xy plane"""
    circle = curve.Circle()
    r = circle.Radius()
    u, v = curve.FirstParameter(), curve.LastParameter()
    if isinstance(curve, BRepAdaptor_Curve) and Topology.is_reversed(curve.Edge()):
        u, v = v, u
    angle = v - u
    length = GCPnts_AbscissaPoint.Length_(curve)
    large_arc_flag = int(length > r * pi)
    sweep_flag = int(circle.Axis().Direction().Z() < 0)
    end = Point(curve.Value(v))
    return f"A {r} {r} {angle} {large_arc_flag} {sweep_flag} {end.x} {end.y}"


def ellipse_to_path(curve: Adaptor3d_Curve) -> str:
    ellipse = curve.Ellipse()
    r = ellipse.MajorRadius()
    r2 = ellipse.MinorRadius()
    if r == r2:
        # Directrix1 throws error if major == minor
        rx = ry = r
    else:
        ax = ellipse.Directrix1()
        ay = ellipse.Directrix2()
        center = Point(ellipse.Location())
        rx = center.distance(ax.Location())
        ry = center.distance(ay.Location())
    u, v = curve.FirstParameter(), curve.LastParameter()
    if isinstance(curve, BRepAdaptor_Curve) and Topology.is_reversed(curve.Edge()):
        u, v = v, u
    angle = v - u
    length = GCPnts_AbscissaPoint.Length_(curve)
    large_arc_flag = int(length > min(rx, ry) * pi)
    sweep_flag = int(ellipse.Axis().Direction().Z() < 0)
    end = Point(curve.Value(v))
    return f"A {rx} {ry} {angle} {large_arc_flag} {sweep_flag} {end.x} {end.y}"


def bezier_to_path(curve: Adaptor3d_Curve) -> str:
    """Convert a bezier curve to svg path data. It must be in the xy plane"""
    bezier = curve.Bezier()
    n = bezier.NbPoles()
    if n == 2:
        end = Point(bezier.Pole(2))
        return f"L {end.x} {end.y}"
    elif n == 3:
        c1 = Point(bezier.Pole(2))
        end = Point(bezier.Pole(3))
        return f"Q {c1.x} {c1.y}, {end.x} {end.y}"
    elif n == 4:
        c1 = Point(bezier.Pole(2))
        c2 = Point(bezier.Pole(3))
        end = Point(bezier.Pole(4))
        return f"C {c1.x} {c1.y}, {c2.x} {c2.y}, {end.x} {end.y}"
    raise ValueError(f"Cannot convert bezier with {n} poles to svg")


def bspline_to_path(curve: Adaptor3d_Curve) -> str:
    bspline = curve.BSpline()
    converter = GeomConvert_BSplineCurveToBezierCurve(bspline)
    data = []
    for i in range(1, converter.NbArcs() + 1):
        bezier = GeomAdaptor_Curve(converter.Arc(i))
        data.append(bezier_to_path(bezier))
    return " ".join(data)


def create_svg_from_wires(wires: list[TopoDS_Wire]) -> etree._Element:
    svg = etree.Element("svg")
    svg.attrib["viewBox"] = "0 0 100 100"
    svg.attrib["xmlns"] = "http://www.w3.org/2000/svg"
    g = etree.SubElement(svg, "g")
    stroke_color = "black"
    for wire in wires:
        edges = Topology(shape=wire).edges
        if len(edges) == 1:
            edge = edges[0]
            topo = Topology(shape=edge)
            curve = BRepAdaptor_Curve(edge)
            start, end = topo.start_point, topo.end_point
            if Topology.is_line(edge):
                node = etree.SubElement(g, "line")
                node.attrib["stroke"] = stroke_color
                node.attrib["x1"] = f"{start.x}"
                node.attrib["y1"] = f"{start.y}"
                node.attrib["x2"] = f"{end.x}"
                node.attrib["y2"] = f"{end.y}"
            elif Topology.is_circle(edge):
                if start == end:
                    c = curve.Circle()
                    center = Point(c.Location())
                    circle = etree.SubElement(g, "circle")
                    circle.attrib["stroke"] = stroke_color
                    circle.attrib["fill"] = "none"
                    circle.attrib["r"] = f"{c.Radius()}"
                    circle.attrib["cx"] = f"{center.x}"
                    circle.attrib["cy"] = f"{center.y}"
                else:
                    path = etree.SubElement(g, "path")
                    path.attrib["stroke"] = stroke_color
                    path.attrib["fill"] = "none"
                    arc = circle_to_path(curve)
                    path.attrib["d"] = f"M {start.x} {start.y} {arc}"
            elif Topology.is_ellipse(edge):
                if start == end:
                    curve = Topology.cast_curve(edge)
                    center = Point(curve.Location())
                    r = curve.MajorRadius()
                    r2 = curve.MinorRadius()
                    ellipse = etree.SubElement(g, "ellipse")
                    ellipse.attrib["stroke"] = stroke_color
                    ellipse.attrib["fill"] = "none"
                    ellipse.attrib["cx"] = f"{center.x}"
                    ellipse.attrib["cy"] = f"{center.y}"
                    if r == r2:
                        ellipse.attrib["rx"] = f"{r}"
                        ellipse.attrib["ry"] = f"{r}"
                    else:
                        ax = curve.Directrix1()
                        ay = curve.Directrix2()
                        angle = ax.Angle(AX)
                        if angle != 0:
                            ellipse.attrib[
                                "transform"
                            ] = f"rotate({angle} {center.x} {center.y})"
                        px = Point(ax.Location())
                        py = Point(ay.Location())
                        if center.distance(px) >= center.distance(py):
                            ellipse.attrib["rx"] = f"{r}"
                            ellipse.attrib["ry"] = f"{r2}"
                        else:
                            ellipse.attrib["rx"] = f"{r2}"
                            ellipse.attrib["ry"] = f"{r}"
                else:
                    path = etree.SubElement(g, "path")
                    path.attrib["stroke"] = stroke_color
                    path.attrib["fill"] = "none"
                    arc = ellipse_to_path(curve)
                    path.attrib["d"] = f"M {start.x} {start.y} {arc}"
            elif Topology.is_bezier_curve(edge):
                path = etree.SubElement(g, "path")
                path.attrib["stroke"] = stroke_color
                path.attrib["fill"] = "none"
                bezier = bezier_to_path(curve)
                path.attrib["d"] = f"M {start.x} {start.y} {bezier}"
            elif Topology.is_bspline_curve(edge):
                path = etree.SubElement(g, "path")
                path.attrib["stroke"] = stroke_color
                path.attrib["fill"] = "none"
                bspline = bspline_to_path(curve)
                path.attrib["d"] = f"M {start.x} {start.y} {bspline}"
            else:
                raise ValueError(f"Cannot convert {curve} to svg")
        else:
            path = etree.SubElement(g, "path")
            data = []
            for edge in edges:
                curve = BRepAdaptor_Curve(edge)
                if not data:
                    start = Topology(shape=edge).start_point
                    data.append(f"M {start.x} {start.y}")
                if Topology.is_line(edge):
                    end = Topology(shape=edge).end_point
                    data.append(f"L {end.x} {end.y}")
                elif Topology.is_circle(edge):
                    data.append(circle_to_path(curve))
                elif Topology.is_ellipse(edge):
                    data.append(ellipse_to_path(curve))
                elif Topology.is_bezier_curve(edge):
                    data.append(bezier_to_path(curve))
                elif Topology.is_bspline_curve(edge):
                    data.append(bspline_to_path(curve))
                else:
                    raise ValueError(f"Cannot convert {curve} to svg")

            if wire.Closed():
                data.append("Z")
            path.attrib["fill"] = "none"
            path.attrib["stroke"] = stroke_color
            path.attrib["d"] = " ".join(data)

    return svg


class SvgExporter(ModelExporter):
    extension = "svg"

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm

            return OptionsForm

    def export(self, shapes: list[Shape]):
        """Export a DeclaraCAD model from an enaml file to an STL based on the
        given options.

        Parameters
        ----------
        options: declaracad.occ.plugin.ExportOptions

        """
        if not shapes:
            raise ValueError("No shapes to export")

        xy = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1), gp_Dir(1, 0, 0))

        wires = []
        for part in shapes:
            projector = HLRAlgo_Projector(xy)
            hlr = HLRBRep_Algo()
            shape = part.render()
            hlr.Add(shape)
            hlr.Projector(projector)
            hlr.Update()
            hlr.Hide()
            result = HLRBRep_HLRToShape(hlr)

            try:
                topo = Topology(shape=result.VCompound())
                wires.extend(Topology.join_edges(topo.edges))
            except RuntimeError:
                pass
            # try:
            #    topo = Topology(shape=result.HCompound())
            #    wires.extend(Topology.join_edges(topo.edges))
            # except RuntimeError:
            #    pass
        if not wires:
            raise RuntimeError("No wires to export")
        doc = create_svg_from_wires(wires)
        with open(self.path, "wb") as f:
            result = etree.tostring(doc, pretty_print=True, xml_declaration=False)
            # print(result)
            f.write(result)
