"""
Copyright (c) 2024, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from math import pi
from typing import Callable as CallableType
from xml.etree import ElementTree as etree

import enaml
from atom.api import Callable, Float, Str
from OCCT.Adaptor3d import Adaptor3d_Curve
from OCCT.BRepAdaptor import BRepAdaptor_Curve
from OCCT.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCCT.BRepLib import BRepLib
from OCCT.GCPnts import GCPnts_AbscissaPoint
from OCCT.GeomAdaptor import GeomAdaptor_Curve
from OCCT.GeomConvert import GeomConvert_BSplineCurveToBezierCurve
from OCCT.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf
from OCCT.HLRAlgo import HLRAlgo_Projector
from OCCT.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCCT.TopoDS import TopoDS_Wire

from declaracad.occ.api import Point, Shape, Topology
from declaracad.occ.impl.occ_shape import AX
from declaracad.viewer.plugin import ModelExporter

AttributeProcessorFn = CallableType[[etree.Element, TopoDS_Wire, int], None]
PostProcessorFn = CallableType[[etree.Element, list[TopoDS_Wire]], None]

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
CC_NS = "http://creativecommons.org/ns#"
DC_NS = "http://purl.org/dc/elements/1.1/"
SVG_NS = "http://www.w3.org/2000/svg"
NSMAP = {
    None: SVG_NS,
    "svg": SVG_NS,
    "rdf": RDF_NS,
    "cc": CC_NS,
    "dc": DC_NS,
}


def fmt(v: float) -> str:
    """Round value to 6 decimal places and convert to a string"""
    return f"{round(v, 6)}"


def pnt(p: Point) -> str:
    """Format a point"""
    return f"{round(p.x, 6)} {round(p.y, 6)}"


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
    if isinstance(curve, BRepAdaptor_Curve):
        cw = Topology.is_clockwise(curve.Edge())
        if Topology.is_reversed(curve.Edge()):
            cw = not cw
        sweep_flag = int(not cw)
    else:
        sweep_flag = int(circle.Axis().Direction().Z() < 0)
    end = Point(curve.Value(v))
    return f"A {fmt(r)} {fmt(r)} {fmt(angle)} {large_arc_flag} {sweep_flag} {pnt(end)}"


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
    if isinstance(curve, BRepAdaptor_Curve):
        sweep_flag = int(not Topology.is_clockwise(curve.Edge()))
    else:
        sweep_flag = int(ellipse.Axis().Direction().Z() < 0)
    end = Point(curve.Value(v))
    return (
        f"A {fmt(rx)} {fmt(ry)} {fmt(angle)} {large_arc_flag} {sweep_flag} {pnt(end)}"
    )


def bezier_to_path(curve: Adaptor3d_Curve) -> str:
    """Convert a bezier curve to svg path data. It must be in the xy plane"""
    bezier = curve.Bezier()
    n = bezier.NbPoles()
    if n == 2:
        end = Point(bezier.Pole(2))
        return f"L {pnt(end)}"
    elif n == 3:
        c1 = Point(bezier.Pole(2))
        end = Point(bezier.Pole(3))
        return f"Q {pnt(c1)}, {pnt(end)}"
    elif n == 4:
        c1 = Point(bezier.Pole(2))
        c2 = Point(bezier.Pole(3))
        end = Point(bezier.Pole(4))
        return f"C {pnt(c1)}, {pnt(c2)}, {pnt(end)}"
    raise ValueError(f"Cannot convert bezier with {n} poles to svg")


def bspline_to_path(curve: Adaptor3d_Curve) -> str:
    bspline = curve.BSpline()
    converter = GeomConvert_BSplineCurveToBezierCurve(bspline)
    data = []
    for i in range(1, converter.NbArcs() + 1):
        bezier = GeomAdaptor_Curve(converter.Arc(i))
        data.append(bezier_to_path(bezier))
    return " ".join(data)


def default_attribute_processor(node: etree.Element, wire: TopoDS_Wire, i: int):
    node.attrib.update(
        {
            "id": f"wire{i}",
            "fill": "none",
            "stroke": "black",
            "stroke-width": "0.1",
            "vector-effect": "non-scaling-stroke",
        }
    )


def create_svg_from_wires(
    wires: list[TopoDS_Wire],
    scale: float = 1,
    attribute_processor: AttributeProcessorFn = default_attribute_processor,
) -> etree.Element:
    svg = etree.Element("svg")
    for ns, url in NSMAP.items():

        if ns is not None:
            etree.register_namespace(ns, url)
            svg.attrib[f"xmlns:{ns}"] = url
        else:
            svg.attrib["xmlns"] = url

    bbox = Topology.bbox(wires)
    t = gp_Trsf()
    t.SetScale(gp_Pnt(0, 0, 0), scale)
    svg.attrib["version"] = "1.1"
    svg.attrib["width"] = f"{fmt(bbox.dx)}mm"
    svg.attrib["height"] = f"{fmt(bbox.dy)}mm"
    svg.attrib["viewBox"] = (
        f"{fmt(bbox.xmin)} {fmt(bbox.ymin)} {fmt(bbox.dx)} {fmt(bbox.dy)}"
    )
    g = etree.SubElement(svg, "g")
    for i, original_wire in enumerate(wires):
        wire = Topology.cast_shape(BRepBuilderAPI_Transform(original_wire, t).Shape())
        edges = Topology(shape=wire).edges
        if len(edges) == 1:
            edge = edges[0]
            topo = Topology(shape=edge)
            curve = BRepAdaptor_Curve(edge)
            start, end = topo.start_point, topo.end_point
            if Topology.is_line(edge):
                node = etree.SubElement(g, "line")
                node.attrib["x1"] = fmt(start.x)
                node.attrib["y1"] = fmt(start.y)
                node.attrib["x2"] = fmt(end.x)
                node.attrib["y2"] = fmt(end.y)
            elif Topology.is_circle(edge):
                if start == end:
                    c = curve.Circle()
                    center = Point(c.Location())
                    node = etree.SubElement(g, "circle")
                    node.attrib["r"] = fmt(c.Radius())
                    node.attrib["cx"] = fmt(center.x)
                    node.attrib["cy"] = fmt(center.y)
                else:
                    node = etree.SubElement(g, "path")
                    arc = circle_to_path(curve)
                    node.attrib["d"] = f"M {pnt(start)} {arc}"
            elif Topology.is_ellipse(edge):
                if start == end:
                    curve = Topology.cast_curve(edge)
                    center = Point(curve.Location())
                    r = curve.MajorRadius()
                    r2 = curve.MinorRadius()
                    node = etree.SubElement(g, "ellipse")
                    node.attrib["cx"] = fmt(center.x)
                    node.attrib["cy"] = fmt(center.y)
                    if r == r2:
                        node.attrib["rx"] = fmt(r)
                        node.attrib["ry"] = fmt(r)
                    else:
                        ax = curve.Directrix1()
                        ay = curve.Directrix2()
                        angle = ax.Angle(AX)
                        if angle != 0:
                            node.attrib["transform"] = (
                                f"rotate({fmt(angle)} {pnt(center)})"
                            )
                        px = Point(ax.Location())
                        py = Point(ay.Location())
                        if center.distance(px) >= center.distance(py):
                            node.attrib["rx"] = fmt(r)
                            node.attrib["ry"] = fmt(r2)
                        else:
                            node.attrib["rx"] = fmt(r2)
                            node.attrib["ry"] = fmt(r)
                else:
                    node = etree.SubElement(g, "path")
                    arc = ellipse_to_path(curve)
                    node.attrib["d"] = f"M {pnt(start)} {arc}"
            elif Topology.is_bezier_curve(edge):
                node = etree.SubElement(g, "path")
                bezier = bezier_to_path(curve)
                node.attrib["d"] = f"M {pnt(start)} {bezier}"
            elif Topology.is_bspline_curve(edge):
                node = etree.SubElement(g, "path")
                bspline = bspline_to_path(curve)
                node.attrib["d"] = f"M {pnt(start)} {bspline}"
            else:
                raise ValueError(f"Cannot convert {curve} to svg")
        else:
            node = etree.SubElement(g, "path")
            data = []
            for edge in edges:
                curve = BRepAdaptor_Curve(edge)
                if not data:
                    start = Topology(shape=edge).start_point
                    data.append(f"M {pnt(start)}")
                if Topology.is_line(edge):
                    end = Topology(shape=edge).end_point
                    data.append(f"L {pnt(end)}")
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
            node.attrib["d"] = " ".join(data)
        attribute_processor(node, original_wire, i)

    return svg


def default_post_processor(doc: etree.Element, wires: list[TopoDS_Wire]):
    # Pretty print
    etree.indent(doc, space=" ")


class SvgExporter(ModelExporter):
    extension = "svg"

    title = Str()
    description = Str()
    author = Str()

    scale = Float(1.0, strict=False)

    #: Processor functions
    attr_processor = Callable(default_attribute_processor)
    post_processor = Callable(default_post_processor)

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
            if isinstance(part, Shape):
                shape = part.render()
            else:
                shape = part
            hlr.Add(shape)
            hlr.Projector(projector)
            hlr.Update()
            hlr.Hide()
            result = HLRBRep_HLRToShape(hlr)

            try:
                result = result.VCompound()
                BRepLib.BuildCurves3d_(result)
                topo = Topology(shape=result)
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
        doc = create_svg_from_wires(wires, self.scale, self.attr_processor)

        # Set metadata
        if self.title or self.author or self.description:
            self.set_metadata(doc)

        # Post process svg
        self.post_processor(doc, wires)

        with open(self.path, "wb") as f:
            result = etree.tostring(doc, encoding="utf-8", xml_declaration=True)
            f.write(result)

    def set_metadata(self, doc: etree.Element):
        """Populate the metadata"""
        metadata = etree.SubElement(doc, "metadata")
        rdf = etree.SubElement(metadata, "{%s}RDF" % RDF_NS)
        work = etree.SubElement(rdf, "{%s}Work" % CC_NS)
        if title := self.title.strip():
            node = etree.SubElement(work, "{%s}title" % DC_NS)
            node.text = title
        if author := self.author.strip():
            creator = etree.SubElement(work, "{%s}creator" % DC_NS)
            agent = etree.SubElement(creator, "{%s}Agent" % CC_NS)
            node = etree.SubElement(agent, "{%s}title" % DC_NS)
            node.text = author
        if desc := self.description.strip():
            node = etree.SubElement(work, "{%s}description" % DC_NS)
            node.text = desc
