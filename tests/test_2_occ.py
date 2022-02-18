"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from math import pi, sqrt
from textwrap import dedent

import pytest
from OCCT.TopoDS import TopoDS_Shape

from declaracad.occ.api import (
    Box,
    Cone,
    Cylinder,
    Direction,
    Ellipse,
    Face,
    Point,
    Rectangle,
    Segment,
    Shape,
    Topology,
    Wire,
    load_model,
)


def test_shape():
    changes = []

    def on_change(change):
        changes.append(change)

    s = Shape()
    s.observe("x", on_change)
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


def test_direction():
    d = Direction(1, 0, 0)
    assert d.reversed() == Direction(-1, 0, 0)
    assert d.rotated(pi / 2) == Direction(0, 1, 0)


def test_topo_cast_shape(qt_app):
    # Invalid type returns None
    assert Topology.cast_shape(None) is None


def test_topo_start_point(qt_app):
    points = [(0, 0), (10, 0)]
    segment = Segment(points=points)
    segment.render()
    assert segment.topology.start_point == points[0]
    assert segment.topology.end_point == points[1]

    assert segment.topology.points[0] == points[0]
    assert segment.topology.points[1] == points[1]

    points = [(10, 0), (0, 0)]
    segment = Segment(points=points)
    segment.render()
    assert segment.topology.start_point == points[0]
    assert segment.topology.end_point == points[1]


def test_topo_is_vertex(qt_app):
    box = Box()
    box.render()
    assert Topology.is_vertex(box.topology.vertices[0])
    assert not Topology.is_vertex(box.topology.edges[0])
    assert not Topology.is_vertex(Box)


def test_topo_is_edge(qt_app):
    box = Box()
    box.render()
    assert not Topology.is_edge(box.topology.vertices[0])
    assert Topology.is_edge(box.topology.edges[0])
    assert not Topology.is_edge(Box)


def test_topo_is_wire(qt_app):
    box = Box()
    box.render()
    assert not Topology.is_wire(box.topology.vertices[0])
    assert Topology.is_wire(box.topology.wires[0])
    assert not Topology.is_wire(Box)


def test_topo_is_face(qt_app):
    box = Box()
    box.render()
    assert not Topology.is_face(box.topology.wires[0])
    assert Topology.is_face(box.topology.faces[0])
    assert not Topology.is_face(Box)


def test_topo_is_shell(qt_app):
    box = Box()
    box.render()
    assert not Topology.is_shell(box.topology.wires[0])
    assert not Topology.is_shell(Box)
    assert Topology.is_shell(box.topology.shells[0])


def test_topo_is_solid(qt_app):
    box = Box()
    box.render()
    assert not Topology.is_solid(box.topology.wires[0])
    assert not Topology.is_solid(Box)
    assert Topology.is_solid(box.proxy.shape)


def test_topo_is_line(qt_app):
    box = Box()
    box.render()
    assert Topology.is_line(box.topology.edges[0])
    assert not Topology.is_line(box.topology.faces[0])


def test_topo_is_plane(qt_app):
    box = Box()
    box.render()
    assert Topology.is_plane(box.topology.faces[0])
    assert not Topology.is_plane(box.topology.edges[0])


def test_topo_is_cylinder(qt_app):
    cylinder = Cylinder()
    cylinder.render()
    assert Topology.is_cylinder(cylinder.topology.faces[0])
    assert not Topology.is_cylinder(cylinder.topology.faces[1])
    assert not Topology.is_cylinder(cylinder.topology.edges[0])


def test_topo_is_cone(qt_app):
    cone = Cone()
    cone.render()
    assert Topology.is_cone(cone.topology.faces[0])
    assert not Topology.is_cone(cone.topology.faces[1])
    assert not Topology.is_cone(cone.topology.edges[0])

    cylinder = Cylinder()
    cylinder.render()
    assert not Topology.is_cone(cylinder.topology.faces[0])


def test_topo_is_circle(qt_app):
    cylinder = Cylinder()
    cylinder.render()
    assert not Topology.is_circle(None)  # Invalid type
    assert Topology.is_circle(cylinder.topology.edges[0])
    assert not Topology.is_circle(cylinder.topology.edges[1])


def test_topo_is_ellipse(qt_app):
    ellipse = Ellipse(major_radius=1, minor_radius=0.5)
    ellipse.render()
    assert Topology.is_ellipse(ellipse.topology.edges[0])


def test_topo_is_clockwise(qt_app):
    rect = Rectangle(width=1, height=2)
    rect.render()
    assert Topology.is_clockwise(rect.topology.wires[0])
    rect = Rectangle(width=1, height=2)
    rect.render()
    assert not Topology.is_clockwise(rect.topology.wires[0].Reversed())


def test_topo_length(qt_app):
    points = [(0, 0), (10, 0)]
    segment = Segment(points=points)
    segment.render()
    assert abs(segment.topology.length - 10) < 1e-6


def test_topo_area(qt_app):
    face = Face(wires=[Rectangle(width=5, height=4).render()])
    face.render()
    assert abs(face.topology.area - 20) < 1e-6


def test_topo_volume(qt_app):
    box = Box(dx=2, dy=1, dz=1)
    box.render()
    assert abs(box.topology.volume - 2 * 1 * 1) < 1e-6


def test_topo_center_point(qt_app):
    box = Box()
    box.render()
    assert box.topology.center_point == Point(0.5, 0.5, 0.5)


def test_topo_curve_bounds(qt_app):
    points = [(0, 0), (10, 0)]
    segment = Segment(points=points)
    segment.render()
    assert segment.topology.curve_bounds == (0, 10)

    with pytest.raises(TypeError):
        box = Box()
        box.render()
        topo = Topology(shape=box.topology.faces[0])
        topo.curve_bounds


def test_topo_surface_bounds(qt_app):
    box = Box(dx=10, dy=1)
    box.render()
    face = Topology(shape=box.topology.faces[5])
    assert face.surface_bounds == (0, 10, 0, 1)

    with pytest.raises(TypeError):
        edge = Topology(shape=box.topology.edges[0])
        edge.surface_bounds


def test_topo_discretize(qt_app):
    points = [(0, 0), (10, 0)]
    segment = Segment(points=points)
    line = segment.render()

    pts = list(Topology.discretize(line, 3, method="abscissa"))
    assert pts == [Point(0, 0), Point(5, 0), Point(10, 0)]

    pts = list(Topology.discretize(line, 1e-4, method="deflection"))
    assert pts == [Point(0, 0), Point(10, 0)]

    with pytest.raises(TypeError):
        box = Box()
        Topology.discretize(box.render(), 2)


def test_topo_bbox(qt_app):
    empty = Topology.bbox([])
    assert empty.center == Point(0, 0)

    box = Box(dx=1, dy=2, dz=3, position=(-0.25, 2, -1))
    box.render()
    bbox = Topology.bbox([box])
    assert bbox.min == Point(-0.25, 2, -1)
    assert bbox.center == Point(0.25, 3, 0.5)
    assert bbox.max == Point(0.75, 4, 2)
    assert abs(bbox.dx - box.dx) < 1e-6
    assert abs(bbox.dy - box.dy) < 1e-6
    assert abs(bbox.dz - box.dz) < 1e-6

    # Enlarge expands box in all directions by the value
    box = Box()
    bbox = Topology.bbox(box.render(), enlarge=2)
    assert bbox.min == Point(-2, -2, -2)
    assert bbox.max == Point(3, 3, 3)


def test_topo_distance(qt_app):
    box = Box()
    box.render()
    cyl = Cylinder(position=(5, 0, 0))
    assert abs(box.topology.min_distance_between(cyl.render()) - 3) < 1e-6
    assert abs(box.topology.max_distance_between(cyl.render()) - 3) < 1e-6


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
