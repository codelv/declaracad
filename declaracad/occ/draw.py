"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 27, 2016

@author: jrm
"""
from math import cos, pi, sin
from typing import Any, Optional

from atom.api import (
    Bool,
    Coerced,
    Dict,
    Enum,
    Float,
    ForwardTyped,
    Instance,
    Int,
    List,
    Range,
    Str,
    Typed,
    observe,
)
from enaml.core.declarative import d_
from OCCT.TopoDS import TopoDS_Face, TopoDS_Shape

from .geom import Direction, Point, coerce_direction, coerce_point
from .shape import ProxyShape, Shape


class ProxyPlane(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Plane)

    def set_bounds(self, bounds):
        raise NotImplementedError


class ProxyVertex(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Vertex)

    def set_marker(self, marker):
        raise NotImplementedError


class ProxyEdge(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Edge)

    def set_surface(self, surface):
        raise NotImplementedError

    def set_as_wire(self, enabled):
        raise NotImplementedError

    def set_line_style(self, style):
        raise NotImplementedError

    def set_line_width(self, width):
        raise NotImplementedError

    def get_value_at(self, t, derivative=0):
        raise NotImplementedError

    def set_solve(self, params):
        raise NotImplementedError

    def set_reverse(self, reverse):
        raise NotImplementedError


class ProxyLine(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Line)

    def set_points(self, points):
        raise NotImplementedError


class ProxySegment(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Segment)


class ProxyArc(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Arc)

    def set_radius(self, r):
        raise NotImplementedError

    def set_alpha1(self, a):
        raise NotImplementedError

    def set_alpha2(self, a):
        raise NotImplementedError

    def set_clockwise(self, clockwise):
        raise NotImplementedError


class ProxyCircle(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Circle)

    def set_radius(self, r):
        raise NotImplementedError


class ProxyEllipse(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Ellipse)

    def set_major_radius(self, r):
        raise NotImplementedError

    def set_minor_radius(self, r):
        raise NotImplementedError


class ProxyHyperbola(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Hyperbola)

    def set_major_radius(self, r):
        raise NotImplementedError

    def set_minor_radius(self, r):
        raise NotImplementedError


class ProxyParabola(ProxyEdge):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Parabola)

    def set_focal_length(self, length: float):
        raise NotImplementedError


class ProxyBSpline(ProxyLine):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: BSpline)


class ProxyBezier(ProxyLine):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Bezier)


class ProxyTrimmedCurve(ProxyLine):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: TrimmedCurve)

    def set_shape(self, shape):
        raise NotImplementedError

    def set_u(self, u: float):
        raise NotImplementedError

    def set_v(self, v: float):
        raise NotImplementedError


class ProxyText(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Text)

    def set_text(self, text: str):
        raise NotImplementedError

    def set_font(self, font: str):
        raise NotImplementedError

    def set_size(self, size: float):
        raise NotImplementedError

    def set_style(self, style: str):
        raise NotImplementedError

    def set_composite(self, composite: bool):
        raise NotImplementedError

    def set_vertical_alignment(self, alignment: str):
        raise NotImplementedError

    def set_horizontal_alignment(self, alignment: str):
        raise NotImplementedError


class ProxyWire(ProxyEdge):
    declaration = ForwardTyped(lambda: Wire)


class ProxyPolyline(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Polyline)

    def set_closed(self, closed: bool):
        raise NotImplementedError

    def set_as_wire(self, as_wire: bool):
        raise NotImplementedError


class ProxyCircuit(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Circuit)

    def set_offset(self, offset: float):
        raise NotImplementedError

    def set_circles(self, circles: list):
        raise NotImplementedError


class ProxyRectangle(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Rectangle)

    def set_rx(self, rx: float):
        raise NotImplementedError

    def set_ry(self, ry: float):
        raise NotImplementedError

    def set_width(self, w: float):
        raise NotImplementedError

    def set_height(self, h: float):
        raise NotImplementedError

    def set_as_face(self, as_face: bool):
        raise NotImplementedError


class ProxySvg(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Svg)

    def set_source(self, source: str):
        raise NotImplementedError

    def set_mirror(self, mirror: bool):
        raise NotImplementedError

    def set_fill_mode(self, mode: str):
        raise NotImplementedError

    def set_center(self, center: bool):
        raise NotImplementedError

    def set_scale(self, scale: float):
        raise NotImplementedError


class ProxyPdf(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Pdf)

    def set_source(self, source: str):
        raise NotImplementedError

    def set_mirror(self, mirror: bool):
        raise NotImplementedError

    def set_fill_mode(self, mode: str):
        raise NotImplementedError

    def set_center(self, center: bool):
        raise NotImplementedError

    def set_scale(self, scale: float):
        raise NotImplementedError


class ProxyMiddlePath(ProxyWire):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: MiddlePath)

    def set_shapes(self, shapes: list):
        raise NotImplementedError

    def set_mode(self, mode: str):
        raise NotImplementedError

    def set_join_type(self, join_type: str):
        raise NotImplementedError


class ProxyBSplineSurface(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: BSplineSurface)

    def set_points(self, points: list[Point]):
        raise NotImplementedError

    def set_deg_min(self, deg: int):
        raise NotImplementedError

    def set_deg_max(self, deg: int):
        raise NotImplementedError

    def set_continuity(self, continuity: Optional[int]):
        raise NotImplementedError

    def set_interpolate(self, interpolate: bool):
        raise NotImplementedError

    def set_periodic(self, periodic: bool):
        raise NotImplementedError


class Plane(Shape):
    """A Point at a specific position.

    Examples
    --------

    Plane:
        position = (10, 100, 0)
        direction = (0, 0, 1)

    """

    proxy = Typed(ProxyPlane)

    #: Bounds of plane (optional) a tuple of [(umin, umin), (vmax, vmax)]
    bounds = d_(List(Coerced(Point, coercer=coerce_point)))


class Vertex(Shape):
    """A Vertex at a specific position.

    Examples
    --------

    Vertex:
        position = (10, 100, 0)

    """

    proxy = Typed(ProxyVertex)

    #: Style marker
    #: TODO: Custom
    marker = d_(
        Enum(
            "plus",
            "point",
            "dot",
            "star",
            "cross",
            "circle",
            "point-in-circle",
            "star-in-circle",
            "plus-in-circle",
            "cross-in-circle",
            "large-ring",
            "medium-ring",
            "small-ring",
            "ball",
        )
    )


class Edge(Shape):
    """An Edge is a base class for Lines and Wires."""

    proxy = Typed(ProxyEdge)

    #: The parametric surface to wrap this edge on
    surface = d_(Instance(TopoDS_Face))

    #: Style for line
    line_style = d_(Enum("solid", "dashed", "dotted", "dot_dash"))

    #: Line width style
    line_width = d_(Float(strict=False))

    #: If True, convert the edge into a wire
    as_wire = d_(Bool())

    #: Solver parameters
    #: When given these will be use to solve for inputs to the shape
    solve = d_(Dict())

    #: Reverse
    reverse = d_(Bool()).tag(view=True)

    @observe("reverse", "as_wire")
    def _update_proxy(self, change):
        super()._update_proxy(change)

    def get_value_at(self, t, derivative=0):
        """Get the value of the curve derivative at t. If the edge has no
        internal parametric curve representation this will throw an error.

        Parameter
        ---------
        t: Float
            The parametric value
        derivative: Int
            The derivative to get (use 0 for position).

        Returns
        -------
        value: Tuple or Float

        """
        return self.proxy.get_value_at(t, derivative)


class Line(Edge):
    """Creates a Line passing through the position and parallel to vector
    given by the direction.

    Attributes
    ----------
        position: Tuple
            The position of the line.
        direction: Tuple
            The direction of the line.

    Examples
    --------

    Line:
        position = (10, 10, 10)
        direction = (0, 0, 1)

    """

    proxy = Typed(ProxyLine)

    #: List of points
    points = d_(List(Coerced(Point, coercer=coerce_point)))

    @property
    def start(self):
        return coerce_point(self.proxy.curve.StartPoint())

    @property
    def end(self):
        return coerce_point(self.proxy.curve.EndPoint())

    @observe("points")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Segment(Line):
    """Creates a line Segment from two or child points. If a position
    and direction are given the points are transformed to align with the
    plane defined by the given position and direction.

    Examples
    --------

    Segment:
        points = ((0, 0, 0), (10, 0, 0)]
    """

    proxy = Typed(ProxySegment)


class Arc(Line):
    """Creates an Arc that can be used to build a Wire.

    Attributes
    ----------

    radius: Float, optional
        The radius of the arc.
    alpha1: Float, optional
        The starting angle of the arc.
    alpha2: Float, optional
        The ending angle of the arc.
    clockwise: Bool
        If using two points this gives the interpolation direction

    Notes
    ------
    An arc can be constructed using:

    1. three child Points
    2. axis, radius, alpha 1, alpha 2
    3. axis, radius, and two child Points
    4. axis, radius, one child Point and alpha 1

    Examples
    ---------
    import math
    Wire:
        Arc:
            attr deg = 5
            radius = 1
            alpha1 = math.radians(deg)
            alpha2 = math.radians(deg+2)
    Wire:
        Arc:
            points = (
                (1, 0, 0),
                (2, 5, 0),
                (3, 0, 0)
            )

    Wire:
        Arc:
            solve = (
                curve.topology.start_tangent,
                end_point,
            )

    """

    proxy = Typed(ProxyArc)

    #: Radius of the circle (optional)
    radius = d_(Float(0, strict=False)).tag(view=True)

    #: Angle circle (optional)
    alpha1 = d_(Float(0, strict=False)).tag(view=True)

    #: 2nd Angle circle (optional)
    alpha2 = d_(Float(0, strict=False)).tag(view=True)

    #: Clockwise (sweep direction, when using two points)
    clockwise = d_(Bool()).tag(view=True)


class Circle(Edge):
    """Creates a Circle.

    Attributes
    ----------

    radius: Float
        The radius of the circle

    Examples
    --------

    Circle:
        radius = 5
        position = (0, 0, 10)
        direction = (1, 0, 0)

    """

    proxy = Typed(ProxyCircle)

    #: Radius of the circle
    radius = d_(Float(1, strict=False)).tag(view=True)

    @observe("radius")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Ellipse(Edge):
    """Creates an Ellipse.

    Attributes
    ----------

    major_radius: Float
        The radius of the circle
    minor_radius: Float
        The second radius of the circle

    Examples
    --------

    Ellipse:
        major_radius = 5
        minor_radius = 7

    """

    proxy = Typed(ProxyEllipse)

    #: Radius of the ellipse
    major_radius = d_(Float(1, strict=False)).tag(view=True)

    #: Minor radius of the ellipse
    minor_radius = d_(Float(1, strict=False)).tag(view=True)

    @observe("major_radius", "minor_radius")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Hyperbola(Edge):
    """Creates a Hyperbola.

    Attributes
    ----------

    major_radius: Float
        The major radius of the hyperbola
    minor_radius: Float
        The minor radius of the hyperbola

    Notes
    ------

    The hyperbola is positioned in the space by the coordinate system A2 such
    that:

    - the origin of A2 is the center of the hyperbola,
    - the "X Direction" of A2 defines the major axis of the hyperbola, that is,
        the major radius MajorRadius is measured along this axis, and
    - the "Y Direction" of A2 defines the minor axis of the hyperbola, that is,
        the minor radius MinorRadius is measured along this axis.

    This class does not prevent the creation of a hyperbola where:
    - MajorAxis is equal to MinorAxis, or
    - MajorAxis is less than MinorAxis. Exceptions Standard_ConstructionError
        if MajorAxis or MinorAxis is negative.

    Raises ConstructionError if MajorRadius < 0.0 or MinorRadius < 0.0 Raised
        if MajorRadius < 0.0 or MinorRadius < 0.0

    Examples
    --------

    Wire:
        Hyperbola:
            major_radius = 5
            minor_radius = 3

    """

    proxy = Typed(ProxyHyperbola)

    #: Major radius of the hyperbola
    major_radius = d_(Float(1, strict=False)).tag(view=True)

    #: Minor radius of the hyperbola
    minor_radius = d_(Float(1, strict=False)).tag(view=True)

    @property
    def start(self):
        return coerce_point(self.proxy.curve.StartPoint())

    @property
    def end(self):
        return coerce_point(self.proxy.curve.EndPoint())

    @observe("major_radius", "minor_radius")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Parabola(Edge):
    """Creates a Parabola with its local coordinate system given by the
    `position` and `direction` and it's focal length `focal_length`.

    Attributes
    ----------

    focal_length: Float
        The focal length of the parabola.

    Notes
    -----
    The XDirection of A2 defines the axis of symmetry of the parabola.
    The YDirection of A2 is parallel to the directrix of the parabola.
    The Location point of A2 is the vertex of the parabola
    Raises ConstructionError if Focal < 0.0 Raised if Focal < 0.0.

    Examples
    ---------

    Wire:
        Parabola:
            focal_length = 10


    """

    proxy = Typed(ProxyParabola)

    #: Focal length of the parabola
    focal_length = d_(Float(1, strict=False)).tag(view=True)

    @property
    def start(self):
        return coerce_point(self.proxy.curve.StartPoint())

    @property
    def end(self):
        return coerce_point(self.proxy.curve.EndPoint())

    @observe("focal_length")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class BSpline(Line):
    """A BSpline built by approximation from the given points.

    Examples
    ---------

    Wire:
        BSpline:
            points = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]

    """

    proxy = Typed(ProxyBSpline)

    #: Use interpolation method. This will automatically be used if periodic
    #: is True or tangents are given.
    interpolate = d_(Bool())

    #: Whether the spline will be periodic
    periodic = d_(Bool())

    # Min and max degree
    deg_min = d_(Int(3))
    deg_max = d_(Int(8))

    #: Degree of continuity
    continuity = d_(Enum(2, 0, 1, 3, None))

    #: List of tangent vectors for each point (optional)
    tangents = d_(List(Coerced(Direction, coercer=coerce_direction)))

    #: List of parameters
    parameters = d_(List(Float(strict=False)))


class Bezier(Line):
    """A Bezier curve built by approximation from the given points.


    Examples
    ---------

    Wire:
        Bezier:
            points = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]

    """

    proxy = Typed(ProxyBezier)


class TrimmedCurve(Edge):
    """A TrimmedCurve built from a curve limited by two parameters.

    Examples
    ---------

    Wire:
        TrimmedCurve:
            u = 0
            v = 2*pi
            Ellipse:
                major_radius = 2*pi
                minor_radius = pi/3


    """

    proxy = Typed(ProxyTrimmedCurve)

    #: Shape to trim. If absent the first child will be used.
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: First Parameter
    u = d_(Float(0, strict=False))

    #: Second Parameter
    v = d_(Float(0, strict=False))


class Wire(Edge):
    """A Wire is a Path or series of Segment, Arcs, etc... All child items
    must be connected or an error will be thrown.

    Attributes
    ----------

    edges: List, optional
        Edges used to build the wire.

    Examples
    ---------

    Wire:
        Polyline:
            closed = True
            points = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]

    """

    proxy = Typed(ProxyWire)

    #: Fixed
    as_wire = True

    #: Edges used to create this wire
    edges = d_(List())

    @observe("edges")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)

    def points_of_discontinuity(self, tolerance: float = 0.5) -> list[Point]:
        """Find points of discontinuity

        Parameters
        ----------
        tolerance: Float
            The tolerance to use

        Returns
        -------
        points: List[Point]
            List of points where there is C1 discontinuity

        """
        points: list[Point] = []

        # Map of vertex to map of curve an derivative
        data: dict[Point, list[tuple[Any, Point]]] = {}
        if not self.proxy_is_active:
            self.render()
        for d in self.topology.curves:
            curve = d["curve"]
            for t in (curve.FirstParameter(), curve.LastParameter()):
                p, v = self.topology.get_value_at(curve, t=t, derivative=1)
                r = data.get(p)
                if r is None:
                    # Hashing doesn't work so check for point equality
                    for k in data:
                        if k.is_equal(p):
                            r = data[k]
                            break
                    if r is None:
                        r = data[p] = []
                r.append((curve, v))

        for p, curves in data.items():
            if len(curves) < 2:
                continue
            v1, v2 = curves[0][1], curves[1][1]
            if v1.is_parallel(v2, tolerance):
                continue  # Continuous
            points.append(p)
        return points


class Polyline(Wire):
    """A Polyline that can be built from any number of points or vertices,
    and consists of a sequence of connected rectilinear edges. If a position
    and direction are given the points are transformed to align with the
    plane defined by the given position and direction.

    Attributes
    ----------
    points: List[Point]
        The points of the polygon.
    closed: Bool
        Automatically close the polygon
    as_face: Bool
        Convert to face if forms a closed wire.
    Examples
    ---------

    Wire:
        Polyline:
            closed = True
            points = [(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)]

    """

    proxy = Typed(ProxyPolyline)

    #: Polyline is closed
    closed = d_(Bool(False)).tag(view=True)

    #: List of points
    points = d_(List(Coerced(Point, coercer=coerce_point)))

    #: Convert into a face
    as_face = d_(Bool())

    @property
    def start(self) -> Point:
        return coerce_point(self.proxy.curve.StartPoint())

    @property
    def end(self) -> Point:
        return coerce_point(self.proxy.curve.EndPoint())

    @observe("closed", "points", "as_face")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Polygon(Polyline):
    """A polyline that follows points on a circle of a given inscribed or
    circumscribed radius.

    Attributes
    ----------
    radius: Float
        Radius of the polygon
    count: Int
        Number of points in the polygon, must be 3 or more.
    inscribed: Bool
        Whether the radius should be interpreted as an "inscribed" or
        "circumscribed" radius. The default is "circumscribed" meaning the
        points will be on the given radius (inside the circle). If
        `inscribed=True` then the midpoint of each segment will be on the
        circle of the given radius (outside the circle).

    Examples
    ---------

    Wire:
        Polygon: # A hexagon of radius 6
            radius = 4
            count = 6

    """

    #: This is fixed
    closed = True

    #: Radius is inscribed
    inscribed = d_(Bool())

    #: Radius of the polygon
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Number of points
    count = d_(Range(low=3)).tag(view=True)

    @observe("radius", "inscribed", "count")
    def _update_points(self, change: dict[str, Any]):
        self.points = self._default_points()

    def _default_points(self) -> list[Point]:
        n = self.count
        r = self.radius
        a = 2 * pi / n
        if self.inscribed:
            r /= cos(pi / n)
        return [Point(x=cos(i * a) * r, y=sin(i * a) * r) for i in range(n)]


def coerce_circle(value: Any) -> Circle:
    from declaracad.occ.api import Topology

    if isinstance(value, (tuple, list)):
        radius = None
        reverse = False
        position = None
        for arg in value:
            if isinstance(arg, (int, float)):
                radius = arg
            elif isinstance(arg, bool):
                reverse = arg
            else:
                position = arg
        return Circle(radius=radius, reverse=reverse, position=position)
    if isinstance(value, dict):
        return Circle(**value)
    if isinstance(value, Circle):
        return value
    if isinstance(value, Shape) and getattr(value, "radius", None):
        return Circle(
            radius=value.radius, direction=value.direction, position=value.position
        )
    if Topology.is_circle(value):
        from OCCT.Geom import Geom_Circle

        curve: Geom_Circle = Topology.cast_curve(value)
        return Circle(radius=curve.Radius(), position=value.Location())
    raise TypeError(f"Cannot coerce {value} to Circle")


class Circuit(Wire):
    """Creates a circuit around a set of circles. Typically
    used for creating belts or chains. A circle a negative radius is used
    to indicate the circuit should go around the "inside".  The reverse
    argument on each circle can be used to reverse the arc direction.

    Examples
    --------
    Circuit:
       circles = [
            (2, (0, 0)),
            (5, (10, 10)),
            (5, (0, 20)),
       ]

    """

    proxy = Typed(ProxyCircuit)

    #: Offset value
    offset = d_(Float(strict=False))

    #: List of tuple of (radius, Point). If radius is negative it is assumed
    #: To mean the inside.
    circles = d_(List(Coerced(Circle, coercer=coerce_circle)))

    @observe("offset", "circles")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Rectangle(Wire):
    """A Wire in the shape of a Rectangle with optional radius'd corners.

    Examples
    ---------

    Wire:
        Rectangle:
            width = 10
            height = 5

    """

    proxy = Typed(ProxyRectangle)

    #: Width of the rectangle
    width = d_(Float(1, strict=False)).tag(view=True)

    #: Height of the rectangle
    height = d_(Float(1, strict=False)).tag(view=True)

    #: Radius of the corner
    rx = d_(Float(0, strict=False)).tag(view=True)
    ry = d_(Float(0, strict=False)).tag(view=True)

    #: Convert into a face
    as_face = d_(Bool())

    @observe("width", "height", "rx", "ry", "as_face")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Text(Shape):
    """Create a shape from a text of a given font.

    Attributes
    ----------

    text: String
        The text to create
    font: String
        The font family to use
    size: Float
        The font size.
    style: String
        Font style
    composite: Bool
        Create a composite curve.


    Examples
    --------

    Text:
        text = "Hello world!"
        font = "Georgia"
        position = (10, 100, 0)

    """

    #: Proxy shape
    proxy = Typed(ProxyText)

    #: Text to display
    text = d_(Str())

    #: Font to use
    font = d_(Str())

    #: Font size
    size = d_(Float(12.0, strict=False))

    #: Font style
    style = d_(Enum("regular", "bold", "italic", "bold-italic"))

    #: Font alignment
    horizontal_alignment = d_(Enum("left", "center", "right"))
    vertical_alignment = d_(Enum("bottom", "center", "top", "topfirstline"))

    #: Composite curve
    composite = d_(Bool(True))

    @observe(
        "text",
        "font",
        "size",
        "style",
        "composite",
        "horizontal_alignment",
        "vertical_alignment",
    )
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Svg(Wire):
    """Creates a wire from a SVG document.

    Attributes
    ----------

    source: String
        Path or svg text to parse

    Examples
    --------

    Svg:
        source = "path/to/file.svg"
        position = (10, 100, 0)

    """

    #: Proxy shape
    proxy = Typed(ProxySvg)

    #: Source file or text
    source = d_(Str())

    #: Mirror y-axis
    mirror = d_(Bool(True))

    #: Automatically shift to center
    center = d_(Bool(False))

    #: Scale. Use this to convert units
    scale = d_(Float(1, strict=False))

    #: Whether to create faces from nodes
    fill_mode = d_(Enum("auto", "always", "never"))

    @observe("source", "fill_mode", "mirror", "center", "scale")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class Pdf(Wire):
    """Creates a wire from a PDF document.

    Attributes
    ----------

    source: String
        Path or pdf to parse

    Examples
    --------

    Svg:
        source = "path/to/file.pdf"
        position = (10, 100, 0)

    """

    #: Proxy shape
    proxy = Typed(ProxyPdf)

    #: Source file or text
    source = d_(Str())

    #: Mirror y-axis
    mirror = d_(Bool(False))

    #: Automatically shift to center
    center = d_(Bool(False))

    #: Scale. Use this to convert units
    scale = d_(Float(25.4 / 72.0, strict=False))

    #: Whether to create faces from nodes
    fill_mode = d_(Enum("auto", "always", "never"))

    @observe("source", "fill_mode", "mirror", "center", "scale")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class MiddlePath(Wire):
    """Create a middle path"""

    proxy = Typed(ProxyMiddlePath)

    #: Must be either empty 1 to 3 elements.
    #: The last two elements represent the start and ending faces or wires.
    shapes = d_(List((Shape, TopoDS_Shape)))

    #: Mode for 2d paths. Normal trims and keep touching edges.
    #: No-trim ignores edge parameters. No touching removes edges touching
    #: the face edge.
    mode = d_(Enum("normal", "not-touching"))

    #: Joint type for 2d paths.
    join_type = d_(Enum("arc", "tangent", "intersection"))

    @observe("shapes", "mode", "join_type")
    def _update_proxy(self, change):
        super()._update_proxy(change)


class BSplineSurface(Shape):
    """Create a BSpline surface from a grid of points"""

    #: A reference to the shape declaration.
    proxy = Typed(ProxyBSplineSurface)

    #: List of list of points
    points = d_(List(List(Coerced(Point, coercer=coerce_point))))

    #: Use interpolation method. This will automatically be used if periodic
    #: is True or tangents are given.
    interpolate = d_(Bool())

    #: Whether the spline will be periodic
    periodic = d_(Bool())

    # Min and max degree
    deg_min = d_(Int(3))
    deg_max = d_(Int(8))

    #: Degree of continuity
    continuity = d_(Enum(2, 0, 1, 3, None))

    @observe("points", "deg_min", "deg_max", "continuity", "interpolate", "periodic")
    def _update_proxy(self, change):
        super()._update_proxy(change)
