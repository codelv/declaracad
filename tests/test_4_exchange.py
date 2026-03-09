"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import os

from OCCT.TopoDS import TopoDS_Shape

from declaracad.occ.api import load_model


def test_load_dxf(qt_app):
    options = {"from_string": True}
    assembly = load_model(
        """
# Created in DeclaraCAD
from declaracad.occ.api import *
from declaracad.occ.loader import LoadedPart

enamldef Assembly(Part):
    LoadedPart: dxf:
        attr outside_wire = self.topology.wires[5]
        attr inside_wires = [w for w in self.topology.wires if w != outside_wire]
        filename = 'examples/models/25-5050.dxf'
        color = 'red'
    Extrude:
        material = 'aluminium'
        vector = (0, 0, 1000)
        Cut:
            color = 'red'
            Face:
                wires = [dxf.outside_wire]
                color = 'red'
            Looper:
                iterable << dxf.inside_wires
                Face:
                    wires = [loop.item]

    """,
        options,
        ".enaml",
    )[0]
    assert isinstance(assembly.render(), TopoDS_Shape)


def test_export_svg(qt_app):
    options = {"from_string": True}
    if os.path.exists("drawing.svg"):
        os.remove("drawing.svg")
    assembly = load_model(
        """
       # Created in DeclaraCAD
from declaracad.occ.api import *

enamldef Drawing(Part):
    Arc:
       radius = 1
       points = [(0, 0), (0, 1)]
    Polyline: polyline:
        points = [(0, 0), (0.5, 0.5), (1, 0)]
    Arc: arc:
        #points = [(0, 0), (1, 0), (0, 1)]
        radius = 1
        points = [(0, 0), (0, 1)]
    Ellipse: ellipse:
       color = 'blue'
       # rotation = pi/2
       major_radius = 4
       minor_radius = 2
    Bezier: quad_bezier:
        position = (1, 0)
        points = [(0, 0), (1, 0), (0, 1)]
    Bezier: cubic_bezier:
        position = (2, 0)
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    Rectangle: rect:
        width = 0.25
        height = 0.125
    Circle: circle:
        radius = 0.1
    BSpline: bspline:
        points = [(0, 0), (0.5, 0.5), (1, 0), (1.5, 0.5)]
    Rectangle: rounded_rect:
        #position = (0, 2)
        rx = 0.5
        width = 2
        height = 3

enamldef Assembly(Part):
    Axis:
        pass

    Drawing: drawing:
        pass

    Export:
        shapes = [drawing]
        options = {"author": "Author"}
        filename = "drawing.svg"
    """,
        options,
        ".enaml",
    )[0]
    assert isinstance(assembly.render(), TopoDS_Shape)
    assert os.path.exists("drawing.svg")
