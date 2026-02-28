# -*- coding: utf-8 -*-
"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""

from math import pi
from typing import Any, ClassVar, Optional, Union

from atom.api import (
    Atom,
    Bool,
    Coerced,
    Dict,
    Enum,
    Event,
    Float,
    FloatRange,
    ForwardInstance,
    ForwardTyped,
    Instance,
    List,
    Property,
    Str,
    Tuple,
    Typed,
    observe,
)
from enaml.colors import Color, ColorMember
from enaml.core.declarative import d_
from enaml.widgets.control import ProxyControl
from enaml.widgets.toolkit_object import ToolkitObject

#: TODO: This breaks the proxy pattern
from OCCT.TopoDS import TopoDS_Face, TopoDS_Shape, TopoDS_Shell

from declaracad.core.utils import log, process_events

from .geom import (
    BBox,
    Direction,
    Point,
    coerce_direction,
    coerce_point,
    coerce_rotation,
    settings,
)
from .materials import Material, Texture


class ProxyExport(ProxyControl):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Export)


class ProxyShape(ProxyControl):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Shape)

    def set_position(self, position: Point):
        pass

    def set_direction(self, direction: Direction):
        pass

    def set_axis(self, axis):
        raise NotImplementedError

    def set_color(self, color: Color):
        pass

    def set_transparency(self, alpha: float):
        pass

    def set_texture(self, texture):
        pass

    def get_bounding_box(self) -> BBox:
        raise NotImplementedError


class ProxyPart(ProxyShape):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Part)

    def set_transform(self, ops):
        raise NotImplementedError


class ProxyFace(ProxyShape):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Face)

    def set_wire(self, wire):
        raise NotImplementedError

    def set_surface(self, surface):
        raise NotImplementedError


class ProxyBox(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Box)

    def set_dx(self, dx: float):
        raise NotImplementedError

    def set_dy(self, dy: float):
        raise NotImplementedError

    def set_dz(self, dz: float):
        raise NotImplementedError


class ProxyCone(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Cone)

    def set_radius(self, r: float):
        raise NotImplementedError

    def set_radius2(self, r: float):
        raise NotImplementedError

    def set_height(self, height: float):
        raise NotImplementedError

    def set_angle(self, angle: float):
        raise NotImplementedError

    def get_apex(self) -> Point:
        raise NotImplementedError


class ProxyCylinder(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Cylinder)

    def set_radius(self, r):
        raise NotImplementedError

    def set_height(self, height):
        raise NotImplementedError

    def set_angle(self, angle):
        raise NotImplementedError


class ProxyTube(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Tube)

    def set_radius(self, r):
        raise NotImplementedError

    def set_radius2(self, r):
        raise NotImplementedError

    def set_height(self, height):
        raise NotImplementedError

    def set_angle(self, angle):
        raise NotImplementedError


class ProxyHalfSpace(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: HalfSpace)

    def set_surface(self, surface):
        raise NotImplementedError

    def set_side(self, side):
        raise NotImplementedError


class ProxyPrism(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Prism)

    def set_shape(self, surface):
        raise NotImplementedError

    def set_vector(self, vector):
        raise NotImplementedError

    def set_infinite(self, infinite):
        raise NotImplementedError

    def set_canonize(self, canonize):
        raise NotImplementedError


class ProxySphere(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Sphere)

    def set_radius(self, r):
        raise NotImplementedError

    def set_angle(self, a):
        raise NotImplementedError

    def set_angle2(self, a):
        raise NotImplementedError

    def set_angle3(self, a):
        raise NotImplementedError


class ProxyTorus(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Torus)

    def set_radius(self, r):
        raise NotImplementedError

    def set_radius2(self, r):
        raise NotImplementedError

    def set_angle(self, a):
        raise NotImplementedError

    def set_angle2(self, a):
        raise NotImplementedError

    def set_angle3(self, a):
        raise NotImplementedError


class ProxyWedge(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Wedge)

    def set_dx(self, dx):
        raise NotImplementedError

    def set_dy(self, dy):
        raise NotImplementedError

    def set_dz(self, dz):
        raise NotImplementedError

    def set_itx(self, itx):
        raise NotImplementedError


class HoleEdgeStyle(Atom):
    kind = Enum("chamfer", "cone")
    distance = Float(strict=False)
    distance2 = Float(strict=False)

    def __init__(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], tuple):
            value = args[0]
            n = len(value)
            if n == 3:
                kind, distance, distance2 = value
                super().__init__(kind=kind, distance=distance, distance2=distance2)
                return
            elif n == 2:
                kind, distance = value
                super().__init__(kind=kind, distance=distance)
                return
        super().__init__(*args, **kwargs)


class ProxyHole(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Hole)

    def set_diameter(self, diameter: float):
        raise NotImplementedError

    def set_depth(self, depth: float):
        raise NotImplementedError

    def set_far_edge(self, value: HoleEdgeStyle):
        raise NotImplementedError

    def set_near_edge(self, value: HoleEdgeStyle):
        raise NotImplementedError


class ProxyRevol(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: Revol)

    def set_shape(self, shape):
        raise NotImplementedError

    def set_angle(self, angle: float):
        raise NotImplementedError


class ProxyRawShape(ProxyShape):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: RawShape)

    def get_shape(self):
        raise NotImplementedError


class ProxyRawPart(ProxyPart):
    #: A reference to the shape declaration.
    declaration = ForwardTyped(lambda: RawPart)

    def get_shapes(self):
        raise NotImplementedError


class Shape(ToolkitObject):
    """Abstract shape component that can be displayed on the screen
    and represented by the framework.

    Notes
    ------

    This shape's proxy holds an internal reference to the underlying shape
    which can be accessed using `self.proxy.shape` if needed. The topology
    of the shape can be accessed using the `self.proxy.topology` attribute.

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyShape)

    #: Whether the shape should be displayed and exported when in a part
    #: If set to false this shape will be excluded from the rendered part
    display = d_(Bool(True))

    #: Description to display in the tooltip when clicked
    description = d_(Str())

    #: The tolerance to use for operations that may require it.
    tolerance = d_(Float(strict=False))

    def _default_tolerance(self) -> float:
        return settings.tolerance

    #: Material
    material = d_(Coerced(Material))

    #: A string representing the color of the shape.
    color = d_(ColorMember())

    #: A string representing the line color of the shape in HLR mode.
    line_color = d_(ColorMember())

    #: A string representing the hidden line color of the shape in wireframe mode.
    wireframe_line_color = d_(ColorMember())

    #: The opacity of the shape used for display.
    transparency = d_(FloatRange(0.0, 1.0, 0.0))

    #: Texture to apply to the shape
    texture = d_(Instance(Texture))

    #: Position alias
    def _get_x(self) -> float:
        return self.position.x

    @observe("position.x")
    def _update_x(self, change: dict[str, Any]):
        self.notify("x", change)

    def _set_x(self, v: float):
        self.position.x = v

    x = d_(Property(_get_x, _set_x))

    def _get_y(self) -> float:
        return self.position.y

    @observe("position.y")
    def _update_y(self, change: dict[str, Any]):
        self.notify("y", change)

    def _set_y(self, v: float):
        self.position.y = v

    y = d_(Property(_get_y, _set_y))

    def _get_z(self) -> float:
        return self.position.z

    @observe("position.z")
    def _update_z(self, change: dict[str, Any]):
        self.notify("z", change)

    def _set_z(self, v: float):
        self.position.z = v

    z = d_(Property(_get_z, _set_z))

    #: A tuple or list of the (x, y, z) position of this shape. This is
    #: coerced into a Point.
    position = d_(Coerced(Point, coercer=coerce_point))

    def _default_position(self) -> Point:
        return Point(0, 0, 0)

    #: A tuple or list of the (u, v, w) normal vector of this shape. This is
    #: coerced into a Vector setting the orientation of the shape.
    #: This is effectively the working plane.
    direction = d_(Coerced(Direction, coercer=coerce_direction))

    def _default_direction(self) -> Direction:
        return Direction(0, 0, 1)

    #: Sets the x-direction of the shape's axis. If None (default) it is calculated using
    #: an axis perpendicular to the normal.
    x_direction = d_(
        Coerced(
            (type(None), Direction),
            coercer=lambda v: None if v is None else coerce_direction(v),
        )
    )

    #: Rotation about the normal vector in radians
    rotation = d_(Coerced(float, coercer=coerce_rotation))

    def _get_axis(self):
        return (self.position, self.direction, self.x_direction, self.rotation)

    def _set_axis(self, axis):
        self.position, self.direction, self.x_direction, self.rotation = axis

    #: A tuple of (position, normal direction, x-direction (optional), rotation) defining the
    #: axis or "workplane" where this shape located.
    axis = d_(Property(_get_axis, _set_axis))

    def _get_topology(self):
        if not self.proxy_is_active:
            self.render()
        return self.proxy.topology

    #: A read only property that accesses the topology of the shape such
    #: as edges, faces, shells, solids, etc....
    topology = Property(_get_topology, cached=True)

    def _get_bounding_box(self) -> Optional[BBox]:
        if self.proxy.shape:
            try:
                return self.proxy.get_bounding_box()
            except Exception as e:
                log.warning(e)
        return None

    #: Bounding box of this shape
    bbox = Property(_get_bounding_box, cached=True)

    @observe(
        "color",
        "transparency",
        "display",
        "texture",
        "position",
        "direction",
        "rotation",
    )
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)

    @observe("proxy.shape")
    def _update_properties(self, change: dict[str, Any]):
        """Clear the cached references when the shape changes."""
        for k in ("bbox", "topology"):
            self.get_member(k).reset(self)
        self.constructed()

    #: Triggered when the shape is constructed
    constructed = d_(Event(), writable=False)

    def activate_proxy(self):
        """Activate the proxy object tree.

        This method should be called by a node to activate the proxy
        tree by making two initialization passes over the tree, from
        this node downward. This method is automatically at the proper
        times and should not normally need to be invoked by user code.

        """
        self.activate_top_down()
        for child in self.children:
            # Make sure each is initialized upon activation
            if not child.is_initialized:
                child.initialize()
            if isinstance(child, ToolkitObject):
                if not child.proxy_is_active:
                    child.activate_proxy()

        # Generating the model can take a lot of time
        # so process events inbetween to keep the UI from freezing
        process_events()

        self.activate_bottom_up()
        self.proxy_is_active = True
        self.activated()

    def render(self) -> TopoDS_Shape:
        """Generates and returns the actual shape from the declaration.
        Enaml does this automatically when it's included in the viewer so this
        is only neede when working with shapes manually.

        Returns
        -------
        shape: TopoDS_Shape
            The shape generated by this declaration.

        """
        if not self.is_initialized:
            self.initialize()
        if not self.proxy_is_active:
            self.activate_proxy()
        return self.proxy.shape

    def __repr__(self) -> str:
        qualname = self.__class__.__qualname__
        addr = f"0x{hex(id(self))}"
        name = self.name
        return f"<{qualname} name={name} at {addr}>"


class Part(Shape):
    """A Part is a compound shape. It may contain
    any number of nested parts and is typically subclassed.

    Attributes
    ----------

    name: String
        An optional name for the part
    description: String
        An optional description for the part

    Examples
    --------

    enamldef Case(Part):
        TopCover:
            # etc..
        BottomCover:
            # etc..

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyPart)

    #: Optional name of the part
    name = d_(Str())

    #: Optional description of the part
    description = d_(Str())

    #: Transform operations
    transform = d_(List())

    #: Set to true to prevent destruction of the shape when removed
    #: from the viewer. You need to manually manage it otherwise it'll
    #: create a memory leak
    cached = d_(Bool(False))

    #: Static cache to store parts in.
    cached_parts: ClassVar[dict[str, "Part"]] = {}

    #: Key use for caching. If you create multiple instances of the same
    #: part use this to distingish between them
    cache_key = d_(Str())

    #: If true, force delete the cache to reload the cached part
    reload = d_(Bool())

    #: Reference to the cached part. If cached is not True this will default
    #: to `self` making it safe to always use this for references.
    cache = ForwardInstance(lambda: Part)

    #: Triggered when the part is rendered in the viewer
    rendered = d_(Event(), writable=False)

    def _default_cache(self):
        return self

    @property
    def shapes(self) -> list[Shape]:
        return [child for child in self.children if isinstance(child, Shape)]

    def initialize(self) -> None:
        if self.cached:
            self.is_initialized = True
            self.initialized()
            self.insert_cached_part()
        else:
            super().initialize()

    def insert_cached_part(self) -> None:
        """Create and insert the cached part into the parent."""
        key = f"{self.__class__.__qualname__}.{self.cache_key}"
        cached_part = Part.cached_parts.get(key)
        if self.reload and cached_part is not None:
            cached_part.cached = False
            cached_part.destroy()
            cached_part = None
        if cached_part is None or cached_part.proxy is None:
            # Create a new part and place in new cached part
            cached_part = self.__class__()
            cached_part.insert_children(self, self.children)
            cached_part.initialize()
            Part.cached_parts[key] = cached_part
            cached_part.cached = True  # Make sure parent does not delete again
        else:
            # Remove children so they do not generate again
            for c in self.children:
                c.destroy()
            del self._children
        self.parent.insert_children(self, [cached_part])
        self.cache = cached_part
        self.proxy = cached_part.proxy

    def destroy(self) -> None:
        """A reimplemented destructor.

        If cached is set to True, destroy removes the shape from the view
        but does not destroy it.

        """
        cached = self.cached
        if cached and self.cache is self:
            # Clear the parent but do not actually destroy
            self.set_parent(None)
            return
        elif cached:
            # This is the part that was used as a placholder for the cached
            # part. Unset the proxy and then destroy so the cached part is
            # left intact.
            self.proxy = None
        super().destroy()


class Face(Shape):
    """A Face turns it's first child Wire into a surface.

    Examples
    --------

    Add a Wire as a child
        Face:
            Wire:
                # etc..

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyFace)

    #: Surface to build on
    surface = d_(Instance((TopoDS_Face, TopoDS_Shell)))

    #: List of wires to use
    wires = d_(List())

    #: Apply shape fixing to the result
    fix = d_(Bool(False))


class Box(Shape):
    """A primitive Box shape.

    Attributes
    ----------

    dx: Float
        Size or width of the box along the x-axis
    dy: Float
        Size or height of the box along the y-axis
    dz: Float
        Size or depth of the box along the z-axis

    Examples
    --------

    Box:
        dx = 3
        dy = 10
        # dx, dy, and dz are all 1 by default if omitted

    """

    #: Proxy shape
    proxy = Typed(ProxyBox)

    #: x size
    dx = d_(Float(1, strict=False)).tag(view=True)

    #: y size
    dy = d_(Float(1, strict=False)).tag(view=True)

    #: z size
    dz = d_(Float(1, strict=False)).tag(view=True)

    # TODO: Handle other constructors

    @observe("dx", "dy", "dz")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Cone(Shape):
    """A primitive Cone shape.

    Attributes
    ----------

    height: Float
        Height of the cone
    radius: Float
        Radius of the base of the cone
    radius2: Float
        Second radius of the base of the cone (to make it oval)
    angle:
        The angle to revolve (in radians) the base profile

    Examples
    --------

    Cone:
        height = 10
        radius = 5
        angle = math.pi/2

    """

    #: Proxy shape
    proxy = Typed(ProxyCone)

    #: Radius
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Radius 2 size
    radius2 = d_(Float(0, strict=False)).tag(view=True)

    #: Height
    height = d_(Float(1, strict=False)).tag(view=True)

    #: Angle
    angle = d_(Float(0, strict=False)).tag(view=True)

    #: Return the apex
    apex = Property(lambda self: self.proxy.get_apex())

    @observe("radius", "radius2", "height", "angle")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Cylinder(Shape):
    """A primitive Cylinder shape.

    Attributes
    ----------

    height: Float
        Height of the cylinder
    radius: Float
        Radius of the base of the cylinder
    angle:
        The angle to revolve (in radians) the base profile.

    Examples
    --------

    Cone:
        height = 10
        radius = 5

    """

    #: Proxy shape
    proxy = Typed(ProxyCylinder)

    #: Radius
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Height
    height = d_(Float(1, strict=False)).tag(view=True)

    #: Angle
    angle = d_(Float(0, strict=False)).tag(view=True)

    @observe("radius", "height", "angle")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Tube(Shape):
    """A tube is a cylinder with the inside cut out. The smaller of radius
    and radius2 will be used as the inner radius.

    Attributes
    ----------

    height: Float
        Height of the tube
    radius: Float
        Outer radius of the base of the tube
    radius2: Float
        Inner radius of the base of the tube
    angle:
        The angle to revolve (in radians) the base profile.

    Examples
    --------

    Tube:
        height = 5
        radius = 1
        radius2 = 0.75


    """

    #: Proxy shape
    proxy = Typed(ProxyTube)

    #: Radius
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Radius 2 size
    radius2 = d_(Float(0, strict=False)).tag(view=True)

    #: Height
    height = d_(Float(1, strict=False)).tag(view=True)

    #: Angle
    angle = d_(Float(0, strict=False)).tag(view=True)

    @observe("radius", "radius2", "height", "angle")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class HalfSpace(Shape):
    """An infinite solid limited by a surface.

    Attributes
    ----------

    surface: Face or Shell
        Surface to divide
    side: Point
        A point on the side of the surface where the half space should be

    Notes
    -----

     A half-space is an infinite solid, limited by a surface. It is built from
     a face or a shell, which bounds it, and with a reference point, which
     specifies the side of the surface where the matter of the half-space is
     located. A half-space is a tool commonly used in topological operations
     to cut another shape

    Examples
    --------

    HalfSpace:
        # Plane at orgiin in z direction
        position = (0, 0, 0)
        direction = (0, 0, 1)
        side = (0, 0, -1) # Negative z side


    """

    #: Proxy shape
    proxy = Typed(ProxyHalfSpace)

    #: Surface that is either a face or a Shell
    surface = d_(Instance((TopoDS_Face, TopoDS_Shell)))

    #: Side of surface where the space is located
    side = d_(Coerced(Point, coercer=coerce_point))

    @observe("surface", "side")
    def _update_proxy(self, change: dict[str, Any]):
        super(HalfSpace, self)._update_proxy(change)


class Prism(Shape):
    """A Prism extrudes a Face into a solid or a Wire into a surface along
    the given vector.

    Attributes
    ----------

    shape: Shape to extrude or None
        Reference to the shape to extrude.
    vector: Tuple of (x, y, z)
        The extrusion vector.
    infinite: Bool
        Whether to extrude an infinte distance along the given vector.
    canonize: Bool
        Attempt to canonize in simple shapes

    Notes
    -----

    The first child node will be used as the shape if none is given.


    Examples
    --------

    Prism:
        Wire:
            Polyline:
                points = [(0,5,0), (2,6,0),  (5,4,0), (0,5,0)]

    """

    #: Proxy shape
    proxy = Typed(ProxyPrism)

    #: Shape to build prism from
    shape = d_(Instance((Shape, TopoDS_Shape))).tag(view=True)

    #: Vector to build prism from, ignored if infinite is true
    vector = d_(Coerced(Direction, coercer=coerce_direction))

    #: Infinite
    infinite = d_(Bool(False)).tag(view=True)

    #: Attempt to canonize
    canonize = d_(Bool(True)).tag(view=True)

    @observe("shape", "vector", "infinite", "canonize")
    def _update_proxy(self, change: dict[str, Any]):
        super(Prism, self)._update_proxy(change)


class Sphere(Shape):
    """A primitive Sphere shape.

    Attributes
    ----------

    radius: Float
        Radius of the sphere
    angle: Float
        The u-angle to revolve (in radians) along the base profile from 0 to 2pi.
    angle2: Float
        The v-min angle to start from (in radians) from -pi/2 to pi/2
    angle3: Float
        The v-max angle to start from (in radians) from -pi/2 to pi/2


    Notes
    --------

    Make a sphere of radius R. For all algorithms The resulting shape is
    composed of:

    - a lateral spherical face
    - Two planar faces parallel to the plane z = 0 if the sphere is truncated
      in the v parametric direction, or only one planar face if angle1 is
      equal to -p/2 or if angle2 is equal to p/2 (these faces are circles in
      case of a complete truncated sphere),
    - and in case of a portion of sphere, two planar faces to shut the shape.
      (in the planes u = 0 and u = angle).


    Examples
    --------

    Sphere:
        radius = 3

    Sphere:
        angle = math.pi/2

    """

    #: Proxy shape
    proxy = Typed(ProxySphere)

    #: Radius of sphere
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Angle of U (fraction of circle)
    angle = d_(FloatRange(low=0.0, high=2 * pi, value=2 * pi)).tag(view=True)

    #: Min Angle of V (fraction of circle in normal direction)
    angle2 = d_(FloatRange(low=-pi / 2, high=pi / 2, value=-pi / 2)).tag(view=True)

    #: Max Angle of V (fraction of circle in normal direction)
    angle3 = d_(FloatRange(low=-pi / 2, high=pi / 2, value=pi / 2)).tag(view=True)

    @observe("radius", "angle", "angle2", "angle3")
    def _update_proxy(self, change: dict[str, Any]):
        super(Sphere, self)._update_proxy(change)


class Torus(Shape):
    """A primitive Torus shape (a ring like shape).

    Attributes
    ----------

    radius: Float
        Radius of the torus
    radius2: Float
        Radius of the torus profile
    angle:  Float
        The angle to revolve the torus (in radians) from 0 to 2 pi.
    angle2: Float
        The angle to revolve the torus profile (in radians) from -pi/2 to pi/2.

    Examples
    --------

    Torus:
        radius = 5

    """

    #: Proxy shape
    proxy = Typed(ProxyTorus)

    #: Radius of sphere
    radius = d_(Float(1, strict=False)).tag(view=True)

    #: Radius 2
    radius2 = d_(Float(0, strict=False)).tag(view=True)

    #: Angle of U (fraction of circle)
    angle = d_(FloatRange(low=0.0, high=2 * pi, value=2 * pi)).tag(view=True)

    #: Start Angle of V (fraction of circle in normal direction)
    angle2 = d_(Float(0, strict=False)).tag(view=True)

    #: Stop Angle of V (fraction of circle in normal direction)
    angle3 = d_(Float(0, strict=False)).tag(view=True)

    @observe("radius", "radius2", "angle", "angle2", "angle3")
    def _update_proxy(self, change: dict[str, Any]):
        super(Torus, self)._update_proxy(change)


class Wedge(Shape):
    """A primitive Wedge shape.

    Attributes
    ----------

    dx: Float
        Size of the wedge along the x-axis
    dy: Float
        Size of the wedge along the y-axis
    dz:  Float
        Size of the wedge along the z-axis
    ltx: Float
        Size of the base before the wedge starts. Must be >= 0.
        Defaults to 0.

    Examples
    --------

    Wedge:
        dy = 5

    """

    #: Proxy shape
    proxy = Typed(ProxyWedge)

    #: x size
    dx = d_(Float(1, strict=False)).tag(view=True)

    #: y size
    dy = d_(Float(1, strict=False)).tag(view=True)

    #: z size
    dz = d_(Float(1, strict=False)).tag(view=True)

    #: z size
    itx = d_(Float(0, strict=False)).tag(view=True)

    # TODO: Handle other constructors

    @observe("dx", "dy", "dz", "itx")
    def _update_proxy(self, change: dict[str, Any]):
        super(Wedge, self)._update_proxy(change)


class Hole(Shape):
    """A primitive Hole shape.

    Attributes
    ----------

    diameter: Float
        The diameter of the hole.
    depth: Float
        The depth of the hole.
    far_edge: Float | Tuple[Float, Float]
        If negative, add a chamfer to the far edge of the hole. If positive add a cone. Far meaning furthest edge from the position.
    near_edge: Float | Tuple[Float, Float]
        If negative, add a chamfer on the near edge of the hole. If positive add a cone. Near meaning closest edge to the position.

    Examples
    --------

    Hole:
        diameter = 4
        depth = 20
        far_edge = ('chamfer', 0.5)
        near_edge =('cone', 0.5)

    """

    #: Proxy shape
    proxy = Typed(ProxyHole)

    #: Hole diameter
    diameter = d_(Float(1, strict=False)).tag(view=True)

    #: Hole depth
    depth = d_(Float(1, strict=False)).tag(view=True)

    #: Far / top edge style
    far_edge = d_(Coerced(HoleEdgeStyle))

    #: Near / Bottom chamfer of the hole
    near_edge = d_(Coerced(HoleEdgeStyle))

    @observe("diameter", "depth", "far_edge", "near_edge")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Revol(Shape):
    """A Revol creates a shape by revolving a profile about an axis.

    Attributes
    ----------

    shape: Shape
        Shape to revolve. If not given, the first child will be used.
    angle: Float
        Angle to revolve (in radians) the base profile.

    Examples
    --------

    # This creates a cone of radius 4 and height 5.

    Revol:
        Wire:
            Polyline:
                points = [(0,0,0), (0,2,5),  (0,5,0), (0,0,0)]

    """

    #: Proxy shape
    proxy = Typed(ProxyRevol)

    #: Shape to build prism from
    shape = d_(Instance(Shape)).tag(view=True)

    #: Angle to revolve
    angle = d_(Float(0, strict=False)).tag(view=True)

    @observe("shape", "angle")
    def _update_proxy(self, change: dict[str, Any]):
        super(Revol, self)._update_proxy(change)


class RawShape(Shape):
    """A RawShape is a shape that delegates shape creation to the declaration.
    This allows custom shapes to be added to the 3D model hierarchy. Users
    should subclass this and implement the `create_shape` method.

    Examples
    --------

    from OCC.TopoDS import TopoDS_Shape
    from OCC.StlAPI import StlAPI_Reader

    class StlShape(RawShape):
        #: Loads a shape from an stl file
        def create_shape(self, parent):
            stl_reader = StlAPI_Reader()
            shape = TopoDS_Shape()
            stl_reader.Read(shape, './models/fan.stl')
            return shape


    """

    #: Reference to the implementation control
    proxy = Typed(ProxyRawShape)

    def create_shape(self, parent):
        """Create the shape for the control.
        This method should create and initialize the shape.

        Parameters
        ----------
        parent : shape or None
            The parent shape for the control.

        Returns
        -------
        result : shape
            The shape for the control.


        """
        raise NotImplementedError

    def get_shape(self):
        """Retrieve the shape for display.

        Returns
        -------
        shape : shape or None
            The toolkit shape that was previously created by the
            call to 'create_shape' or None if the proxy is not
            active or the shape has been destroyed.
        """
        if self.proxy_is_active:
            return self.proxy.get_shape()


class RawPart(Shape):
    """A RawPart is a part that delegates creation to the declaration.
    This allows custom shapes to be added to the 3D model hierarchy. Users
    should subclass this and implement the `create_shapes` method.

    Examples
    --------

    from OCC.TopoDS import TopoDS_Shape
    from OCC.StlAPI import StlAPI_Reader

    class StlShape(RawShape):
        #: Loads a shape from an stl file
        def create_shape(self, parent):
            stl_reader = StlAPI_Reader()
            shape = TopoDS_Shape()
            stl_reader.Read(shape, './models/fan.stl')
            return shape


    """

    #: Reference to the implementation control
    proxy = Typed(ProxyRawPart)

    def create_shapes(self, parent):
        """Create the shape for the control.
        This method should create and initialize the shape.

        Parameters
        ----------
        parent : shape or None
            The parent shape for the control.

        Returns
        -------
        result : List[shape]
            The shapes for the control.


        """
        raise NotImplementedError

    def get_shapes(self):
        """Retrieve the shapes for display.

        Returns
        -------
        shapes : List[shape] or None
            The toolkit shape that was previously created by the
            call to 'create_shapes' or None if the proxy is not
            active or the shape has been destroyed.
        """
        if self.proxy_is_active:
            return self.proxy.get_shapes()


class TopoShape(RawShape):
    """A declaration for inserting an existing TopoDS_Shape somewhere into a
    DeclaraCAD tree.

    """

    shape = d_(Instance(TopoDS_Shape))

    def create_shape(self, parent):
        return self.shape

    def get_shape(self):
        return self.shape


class Export(ToolkitObject):
    """A block which exports the shape"""

    #: Disable export
    disabled = d_(Bool())

    #: Shapes to export
    shapes = d_(List((Shape, TopoDS_Shape)))

    #: Export filename
    filename = d_(Str())

    #: Export options
    options = d_(Dict())
