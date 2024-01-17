"""
Copyright (c) 2024, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os

import enaml
from atom.api import Bool, Float
from lxml import etree
from OCCT.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCCT.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCCT.HLRAlgo import HLRAlgo_Projector
from OCCT.TopoDS import TopoDS_Wire

from declaracad.occ.api import Shape, Topology, Point
from declaracad.viewer.plugin import ModelExporter


def create_svg_from_wires(wires: list[TopoDS_Wire]) -> etree._Element:
    svg = etree.Element("svg")
    svg.attrib["viewBox"] = "0 0 100 100"
    svg.attrib["xmlns"] = "http://www.w3.org/2000/svg"

    stroke_color = "black"
    for wire in wires:
        edges = Topology(shape=wire).edges
        if len(edges) == 1:
            edge = edges[0]
            topo = Topology(shape=edge)
            start, end = topo.start_point, topo.end_point
            if Topology.is_line(edge):
                line = etree.SubElement(svg, "line")
                line.attrib["x1"] = start.x
                line.attrib["y1"] = start.y
                line.attrib["x2"] = end.x
                line.attrib["y2"] = end.y
                line.attrib["stroke"] = stroke_color
            elif Topology.is_circle(edge):
                curve = Topology.cast_curve(edge)
                center = Point(curve.Location())
                r = curve.Radius()
                if start == end:
                    circle = etree.SubElement(svg, "circle")
                    circle.attrib["r"] = r
                    circle.attrib["cx"] = center.x
                    circle.attrib["cy"] = center.y
                    circle.attrib["stroke"] = stroke_color
                else:
                    path = etree.SubElement(svg, "path")
                    angle = 0
                    large_arc_flag = 0
                    sweep_flag = 0
                    path.attrib["d"] = " ".join((
                        f"M {start.x} {start.y}",
                        f"A {r} {r} {angle} {large_arc_flag} {sweep_flag} {end.x} {end.y}"
                    ))
                    path.attrib["stroke"] = stroke_color

            # elif Topology.is_ellipse(edge):
            #     curve = Topology.cast_curve(edge)
            #     center = Point(curve.Location())
            #     if start == end:
            #         ellipse = etree.SubElement(svg, "ellipse")
            #         ellipse.attrib["r"] = r
            #         ellipse.attrib["cx"] = center.x
            #         ellipse.attrib["cy"] = center.y
            #         ellipse.attrib["rx"] = center.y
            #         circle.attrib["stroke"] = stroke_color
            else:
                curve = Topology.cast_curve(edge)
                raise ValueError(f"Cannot convert {curve}")
        else:
            path = etree.SubElement(svg, "path")
            data = []
            for edge in edges:
                topo = Topology(shape=edge)
                start, end = topo.start_point, topo.end_point
                if not data:
                    data.append(f"M {start.x} {start.y}")
                if Topology.is_line(edge):
                    data.append(f"L {end.x} {end.y}")
                elif Topology.is_circle(edge):
                    # TODO: Arc
                    data.append(f"A {end.x} {end.y}")
                elif Topology.is_bezier_curve(edge):
                    # TODO: Arc
                    bezier = Topology.cast_curve(edge)
                    if bezier.NbPoles() == 2:
                        c1 = Point(bezier.Pole(1))
                        data.append(f"Q {c1.x} {c1.y}, {end.x} {end.y}")
                    elif bezier.NbPoles() == 3:
                        c1 = Point(bezier.Pole(1))
                        c1 = Point(bezier.Pole(2))
                        data.append(f"C {c1.x} {c1.y}, {c2.x} {c2.y}, {end.x} {end.y}")
                    else:
                        raise ValueError("Cannot convert bezier with more than 3 poles")
                else:
                    curve = Topology.cast_curve(edge)
                    raise ValueError(f"Cannot convert {curve}")
                last_point = end

            if wire.Closed():
                data.append("Z")
            path.attrib["d"] = " ".join(data)
            path.attrib["stroke"] = stroke_color

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

        xy = gp_Ax2(
            gp_Pnt(0, 0, 0),
            gp_Dir(0, 0, 1),
            gp_Dir(1, 0, 0)
        )

        projector = HLRAlgo_Projector(xy)

        hlr = HLRBRep_Algo()
        for part in shapes:
            shape = part.render()
            hlr.Add(shape)

        hlr.Projector(projector)
        hlr.Update()
        hlr.Hide()

        result = HLRBRep_HLRToShape(hlr)

        wires = []
        try:
            topo = Topology(shape=result.VCompound())
            wires.extend(Topology.join_edges(topo.edges))
        except RuntimeError:
            pass
        try:
            topo = Topology(shape=result.HCompound())
            wires.extend(Topology.join_edges(topo.edges))
        except RuntimeError:
            pass
        if not wires:
            raise RuntimeError("No wires to export")
        doc = create_svg_from_wires(wires)
        with open(self.path, 'wb') as f:
            result = etree.tostring(
                doc,
                pretty_print=True,
                xml_declaration=False
            )
            print(result)
            f.write(result)
