"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import pytest
from textwrap import dedent

from OCCT.TopoDS import TopoDS_Shape
from declaracad.occ.api import load_model, Point, Shape, Segment


def test_shape():
    changes = []

    def on_change(change):
        changes.append(change)

    s = Shape()
    s.observe('x', on_change)
    s.position.x = 2
    s.x = 3
    assert s.position.x == 3
    assert len(changes) == 2


def test_point():
    assert (Point(0, 0) + (1, 1)) == Point(1, 1)
    assert (Point(1, 1) - (2, 1)) == Point(-1, 0)
    assert Point().distance(Point(3, 4)) == 5
    assert Point().midpoint(Point(4, 2)) == Point(2, 1)
    print(Point())

    assert Point(1, 2, 3)[:] == (1, 2, 3)
    p = Point(1, 2, 3)
    p[1] = 4
    assert p.y == 4

    assert Point(1, 2, 3) * 2 == Point(2, 4, 6)
    assert Point(2, 4, 6) / 2 == Point(1, 2, 3)

    with pytest.raises(TypeError):
        Point(1, 2, 3) / Point(1, 2, 3)

    with pytest.raises(TypeError):
        Point(1, 2, 3) * Point(1, 2, 3)


def test_point_offset():
    p = Point(0, 0, 0)
    a = p.offset(5, (1, 0, 0))

    p = Point(1, 0, 0)
    a = p.offset(5, (1, 0, 0))
    assert a == Point(6, 0, 0)

    a = p.offset(5, (0, 1, 0))
    assert a == Point(1, 5, 0)


def test_topo_start_point(qt_app):
    points = [(0, 0), (10, 0)]
    segment = Segment(points=points)
    segment.render()
    assert segment.topology.start_point == points[0]
    assert segment.topology.end_point == points[-1]
    points = [(10, 0), (0, 0)]
    segment = Segment(points=points)
    segment.render()
    assert segment.topology.start_point == points[0]
    assert segment.topology.end_point == points[-1]




TEMPLATE = """
import math
from declaracad.occ.api import *

enamldef Assembly(Part):
%s

"""

TESTS = {
    "arc-1": """
    Arc: # circle
        radius = 2
        points = [(0, 1), (0, 1)]
    """,
    "arc-2": """
    Arc:
        radius = 2
        alpha1 = math.pi/4
        points = [(0, 1)]
    """,
    "arc-3": """
    Arc:
        radius = 2
        alpha1 = math.pi
        alpha2 = 3/2*math.pi
    """,
    "arc-4": """
    Arc:
        radius = 2
        clockwise = True
        points = [(0, 1), (1, 1)]
    """,
    "arc-5": """
    Arc:
        radius = 2
        reverse = True
        points = [(0, 1), (1, 1)]
    """,
    "line-2": """
    Line:
        direction = (0, 1, 0)
        points = [(2, 0, 0)] # Offset point
    """,
    "vertex": """
    Vertex:
        position = (1, 2, 0)
    """,
    "box1": """
     Box:
         position = (10, 2, 30)
     """,
    "cone1": """
     Cone:
         radius = 1
         height = 5
     """,
    "cylinder1": """
     Cylinder:
         radius = 2
     """,
    "cylinder2": """
    Cylinder:
        angle = 30*math.pi
    """,
    "sphere": """
    Sphere:
        radius = 2
    """,
    "sphere-2": """
    Sphere:
        angle = math.pi/4
    """,
    "sphere-3": """
    Sphere:
        angle = math.pi/4
        angle2 = math.pi/4
    """,
    "sphere-4": """
    Sphere:
        angle = math.pi/4
        angle2 = math.pi/4
        angle3 = math.pi/4
    """,
    "wedge": """
    Wedge:
        dy = 2
    """,
    "torus": """
    Torus:
        radius = 2
        radius2 = 0.4
    """,
    "torus-2": """
    Torus:
        radius = 5
        radius2 = 1
        angle = math.pi
    """,
    "torus-3": """
    Torus:
        radius = 5
        radius2 = 1
        angle = math.pi
        angle2 = math.pi/4
    """,
    "tube-1": """
    Tube:
        radius = 5
        radius2 = 1
    """,
    "tube-2": """
    Tube:
        radius = 5
        radius2 = 6
    """,
    "Tube-3": """
    Tube:
        radius = 5
        radius2 = 0
    """,
    "Tube-4": """
    Tube:
        radius = 5
        radius2 = 3
        angle = math.pi
    """,
    "prism": """
    Prism:
        Wire:
            Polyline:
                points = [(0,5,0), (2,6,0),  (5,4,0), (0,5,0)]
    """,
    "revol": """
    Revol:
        Wire:
            Polyline:
                points = [(0,0,0), (0,2,5),  (0,5,0), (0,0,0)]
    """,
    "circle": """
    Wire:
        Circle:
            radius = 10
    """,
    "ellipse": """
    Wire:
        Ellipse:
            major_radius = 3
            minor_radius = 2
    """,
    "polygon": """
    Wire:
        Polyline:
            points = [(0,0,0), (0,2,5),  (0,5,0), (0,0,0)]
    """,
    "bezier": """
    Wire:
        color = 'blue'
        Bezier: b1:
            points = [ (1,5,2),  (2,6,1),  (3,4,5)]
    """,
    "bspline": """
    Wire:
        color = 'green'
        BSpline: bspline:
            attr r = 3
            points = [
                (r*math.sin(math.pi/2*i),r*math.cos(math.pi/2*i), i/4)
                for i in range(21)
            ]

    """,
    "bspline-2": """
    BSpline:
        tangents = [(1, 0, 0), (0, 1, 0)]
        points = [
            (1, 0, 0),
            (2, -0.5, 0),
            (3, 1, 0),
        ]
    """,
    "hyperbola": """
    Hyperbola:
        major_radius = 10
        minor_radius = 1
    """,
    "cut": """
    Cut:
        Box:
            pass
        Box:
            position = (0.5, 0.5, 0)
    """,
    "fuse": """
    Fuse:
        fix = True
        Box:
            pass
        Box:
            position = (0.5, 0.5, 0)
    """,
    "common": """
    Common:
        unify = True
        Box:
            pass
        Box:
            position = (0.5, 0.5, 0)
    """,
}


@pytest.mark.parametrize("name", TESTS.keys())
def test_shapes_render(qt_app, name):
    source = TEMPLATE % TESTS[name]
    options = {"from_string": True}
    assembly = load_model(source, options, ".enaml")[0]
    assert isinstance(assembly.render(), TopoDS_Shape)
