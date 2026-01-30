"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 28, 2016

@author: jrm
"""

from typing import Any, Optional, Union

from atom.api import (
    Atom,
    Bool,
    Coerced,
    Enum,
    Float,
    ForwardTyped,
    Instance,
    List,
    Tuple,
    Typed,
    observe,
)
from enaml.core.declarative import d_

from .geom import Direction, Point, coerce_direction, coerce_point
from .shape import ProxyShape, Shape, TopoDS_Shape


class ProxyOperation(ProxyShape):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Operation)

    def set_fix(self, fix: bool):
        raise NotImplementedError


class ProxyBooleanOperation(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: BooleanOperation)

    def set_disabled(self, disabled: bool):
        raise NotImplementedError

    def set_shape1(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_shape2(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_unify(self, unify: bool):
        raise NotImplementedError

    def set_parallel(self, parallel: bool):
        raise NotImplementedError


class ProxyCommon(ProxyBooleanOperation):
    declaration = ForwardTyped(lambda: Common)


class ProxyCut(ProxyBooleanOperation):
    declaration = ForwardTyped(lambda: Cut)


class ProxyFuse(ProxyBooleanOperation):
    declaration = ForwardTyped(lambda: Fuse)


class ProxySplit(ProxyBooleanOperation):
    declaration = ForwardTyped(lambda: Split)


class ProxyIntersection(ProxyBooleanOperation):
    declaration = ForwardTyped(lambda: Intersection)


class ProxyFillet(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Fillet)

    def set_disabled(self, disabled: bool):
        raise NotImplementedError

    def set_radius(self, r: float):
        raise NotImplementedError

    def set_operations(self, operations: list):
        raise NotImplementedError

    def set_shape_type(self, shape_type: str):
        raise NotImplementedError


class ChamferData(Atom):
    distance = Float(strict=False)
    distance2 = Float(strict=False)
    angle = Float(strict=False)
    edge = Typed(TopoDS_Shape)
    face = Typed(TopoDS_Shape)


class ProxyChamfer(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Chamfer)

    def set_disabled(self, disabled: bool):
        raise NotImplementedError

    def set_distance(self, d: float):
        raise NotImplementedError

    def set_distance2(self, d: float):
        raise NotImplementedError

    def set_operations(self, operations: list):
        raise NotImplementedError


class ProxyOffset(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Offset)

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_closed(self, closed: bool):
        raise NotImplementedError

    def set_offset(self, offset: float):
        raise NotImplementedError

    def set_offset_mode(self, mode: str):
        raise NotImplementedError

    def set_intersection(self, enabled: bool):
        raise NotImplementedError

    def set_join_type(self, mode: str):
        raise NotImplementedError

    def set_as_face(self, enabled: bool):
        raise NotImplementedError

    def set_disabled(self, disabled: bool):
        raise NotImplementedError


class ProxyOffsetShape(ProxyOffset):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: OffsetShape)

    def set_solid(self, solid: bool):
        raise NotImplementedError


class ProxyThickSolid(ProxyOffset):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: ThickSolid)

    def set_faces(self, faces: list):
        raise NotImplementedError


class ProxyPipe(ProxyOffset):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Pipe)

    def set_spline(self, spline: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_profile(self, profile: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_fill_mode(self, mode: str):
        raise NotImplementedError


class ProxyEvolved(ProxyOffset):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Evolved)

    def set_spline(self, spline: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_profile(self, profile: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError


class ProxyAbstractRibSlot(ProxyOperation):
    #: Abstract class

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_contour(self, contour: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_plane(self, plane: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_fuse(self, fuse: bool):
        raise NotImplementedError


class ProxyDraftAngle(ProxyOperation):
    def set_disabled(self, disabled: bool):
        raise NotImplementedError

    def set_angle(self, angle: float):
        raise NotImplementedError

    def set_faces(self, faces: list):
        raise NotImplementedError

    def set_operations(self, operations: list):
        raise NotImplementedError


class ProxyLinearForm(ProxyAbstractRibSlot):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: LinearForm)

    def set_direction1(self, direction: Optional[Union[Direction, tuple, list]]):
        raise NotImplementedError

    def set_modify(self, modify: bool):
        raise NotImplementedError


class ProxyRevolutionForm(ProxyAbstractRibSlot):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: RevolutionForm)

    def set_height1(self, height: float):
        raise NotImplementedError

    def set_height2(self, height: float):
        raise NotImplementedError

    def set_sliding(self, sliding: bool):
        raise NotImplementedError


class ProxyThruSections(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: ThruSections)

    def set_solid(self, solid: bool):
        raise NotImplementedError

    def set_ruled(self, ruled: bool):
        raise NotImplementedError

    def set_fix(self, fix: bool):
        raise NotImplementedError

    def set_precision(self, pres3d: float):
        raise NotImplementedError

    def set_sections(self, sections: list):
        raise NotImplementedError


class ProxyTransform(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Transform)

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_operations(self, operations: list["TransformOperation"]):
        raise NotImplementedError


class ProxySew(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Sew)

    def set_solid(self, solid: bool):
        raise NotImplementedError


class ProxyGlue(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Glue)


class ProxyNormalProjection(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: NormalProjection)

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_max_distance(self, distance: float):
        raise NotImplementedError


class ProxyExtend(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: Extend)

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_mode(self, mode: str):
        raise NotImplementedError

    def set_operations(self, operations: list):
        raise NotImplementedError


class ProxyRemoveFeatures(ProxyOperation):
    #: A reference to the Shape declaration.
    declaration = ForwardTyped(lambda: RemoveFeatures)

    def set_shape(self, shape: Optional[Union[Shape, TopoDS_Shape]]):
        raise NotImplementedError

    def set_disabled(self, disabled: bool):
        raise NotImplementedError

    def set_parallel(self, parallel: bool):
        raise NotImplementedError

    def set_features(self, featres: list):
        raise NotImplementedError


class Operation(Shape):
    """Base class for Operations that are applied to other shapes."""

    #: Reference to the implementation control
    proxy = Typed(ProxyOperation)

    #: Attempt to fix issues in the resulting shape
    fix = d_(Bool(False))

    @observe("fix")
    def _update_proxy(self, change: dict[str, Any]):
        if change["name"] == "axis":
            dx, dy, dz = self.x, self.y, self.z
            if change.get("oldvalue"):
                old = change["oldvalue"].Location()
                dx -= old.X()
                dy -= old.Y()
                dz -= old.Z()
            for c in self.children:
                if isinstance(c, Shape):
                    c.position = (c.x + dx, c.y + dy, c.z + dz)
        super(Operation, self)._update_proxy(change)


class BooleanOperation(Operation):
    """A base class for a boolean operation on two or more shapes.

    Attributes
    ----------

    shape1: Shape
        The first shape argument of the operation.
    shape2: Shape
        The second shape argument of the operation.

    """

    shape1 = d_(Instance(object))

    shape2 = d_(Instance(object))

    #: Disable the operation (the result will be the first shape or child)
    disabled = d_(Bool(False))

    #: Unify using ShapeUpgrade_UnifySameDomain
    unify = d_(Bool(False))

    #: If True, put all children in one operation otherwise
    #: perform a boolean operation with each child one at a time
    parallel = d_(Bool(False))

    @observe("shape1", "shape2", "unify", "parallel", "disabled")
    def _update_proxy(self, change: dict[str, Any]):
        super(BooleanOperation, self)._update_proxy(change)


class Common(BooleanOperation):
    """An operation that results in the common volume of the two shapes.
    This operation is repeated to give the intersection all child shapes.

    Examples
    ----------

    Common:
        Box:
            pass
        Circle:
            radius = 2
        Torus:
            radius = 1


    """

    #: Reference to the implementation control
    proxy = Typed(ProxyCommon)


class Cut(BooleanOperation):
    """An operation that results in the subtraction of the second and
    following shapes the first shape.  This operation is repeated for all
    additional child shapes if more than two are given.

    Examples
    ----------

    Cut:
        Box:
            dx = 2
            dy = 2
            dz = 2
        Box:
            pass

        # etc...

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyCut)


class Fuse(BooleanOperation):
    """An operation that results in the addition all of the child shapes.

    Examples
    ----------

    Fuse:
        Box:
            pass
        Box:
            position = (1,0,0)

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyFuse)


class Split(BooleanOperation):
    """An operation that splits the first shape by all of the other shapes.

    Examples
    ----------

    Split:
        # Splits the sphere along the x axis
        Sphere:
            radius = 2
        Plane:
            position = (1,0,0)

    """

    #: Reference to the implementation control
    proxy = Typed(ProxySplit)


class Intersection(BooleanOperation):
    """An operation that gives the intersection by the first shape and all of
    the other shapes. The result is always an Edge, Wire, or Vertex. To get a
    filled shape, use the `Common` operation instead.


    Examples
    ----------

    Intersection:
        # Draws the intersection wires of the box sliced by the plane
        Box:
            pass
        Plane:
            position = (1/2,0,0)

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyIntersection)


class Fillet(Operation):
    """Applies fillet operation to the first child shape.

    Attributes
    ----------

    shape: String
        The fillet shape type apply
    radius: Float
        Radius of the fillet. Must be less than the face width.
    operations: List of edges, optional
        List of edges to apply the operation to. If not given all edges will
        be used.  Used in conjunction with the `topology.edges` attribute.

    Examples
    --------

    Fillet:
        #: Fillet the first 4 edges of the box (left side)
        operations = [e for i, e in enumerate(box.topology.edges) if i < 4]
        radius = 0.1
        Box: box:
            pass

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyFillet)

    #: If True, don't apply the fillet (for debugging)
    disabled = d_(Bool())

    #: Fillet shape type
    shape_type = d_(Enum("rational", "angular", "polynomial")).tag(
        view=True, group="Fillet"
    )

    #: Radius of fillet
    radius = d_(Float(1, strict=False)).tag(view=True, group="Fillet")

    #: Edges to apply fillet to and parameters
    #: Leave blank to use all edges of the shape
    operations = d_(List()).tag(view=True, group="Fillet")

    @observe("shape_type", "radius", "operations", "disabled")
    def _update_proxy(self, change: dict[str, Any]):
        super(Fillet, self)._update_proxy(change)


class Chamfer(Operation):
    """Applies Chamfer operation to the first child shape.

    Attributes
    ----------

    distance: Float
       The distance of the chamfer to apply
    distance2: Float
       The second distance of the chamfer to apply
    operations: List of edges or faces, optional
       List of edges or faces to apply the operation to. If not given the first
       face will be used.  Used in conjunction with the `topology` attribute.

    Examples
    --------

    Chamfer:
        #: Fillet the top of the cylinder
        operations = [cyl.topology.faces[0]]
        distance = 0.2
        Cylinder: cyl:
           pass

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyChamfer)

    #: If True, don't apply the chamfer (for debugging)
    disabled = d_(Bool())

    #: Distance of chamfer
    distance = d_(Float(1, strict=False)).tag(view=True, group="Chamfer")

    #: Second of chamfer (leave 0 if not used)
    distance2 = d_(Float(0, strict=False)).tag(view=True, group="Chamfer")

    #: Edges or faces to apply chamfer to
    operations = d_(List()).tag(view=True, group="Chamfer")

    @observe("distance", "distance2", "operations", "disabled")
    def _update_proxy(self, change: dict[str, Any]):
        super(Chamfer, self)._update_proxy(change)


class Offset(Operation):
    """An operation that create an Offset wire or face of the first child shape.

    Attributes
    ----------

    offset: Float
        The offset distance
    offset_mode: String
        Defines the construction type of parallels applied to the free edges
        of the shape
    intersection: Bool
        Intersection specifies how the algorithm must work in order to limit
        the parallels to two adjacent shapes
    join_type: String
        Defines how to fill the holes that may appear between parallels to
        the two adjacent faces
    disabled: Bool


    Examples
    --------

    See examples/operations.enaml

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyOffset)

    #: Whether the offset should be closed
    closed = d_(Bool(True))

    #: Offset
    offset = d_(Float(1, strict=False)).tag(view=True, group="Offset")

    #: Make the offset at a distance parallel to the normal plane.
    normal_distance = d_(Float(0, strict=False))

    #: Offset mode
    offset_mode = d_(Enum("skin", "pipe", "recto_verso")).tag(view=True, group="Offset")

    #: Intersection
    intersection = d_(Bool(False)).tag(view=True, group="Offset")

    #: Join type
    join_type = d_(Enum("arc", "tangent", "intersection")).tag(
        view=True, group="Offset"
    )

    #: If True, convert the wire into a face
    as_face = d_(Bool())

    #: The shape to offset if given
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: Disble operation
    disabled = d_(Bool())

    @observe(
        "offset",
        "offset_mode",
        "intersection",
        "join_type",
        "closed",
        "normal_distance",
        "shape",
        "as_face",
        "disabled",
    )
    def _update_proxy(self, change: dict[str, Any]):
        super(Offset, self)._update_proxy(change)


class OffsetShape(Offset):
    """An operation that create an OffsetShape from the first child shape.

    Attributes
    ----------

    offset: Float
        The offset distance
    offset_mode: String
        Defines the construction type of parallels applied to the free edges
        of the shape
    intersection: Bool
        Intersection specifies how the algorithm must work in order to limit
        the parallels to two adjacent shapes
    join_type: String
        Defines how to fill the holes that may appear between parallels to
        the two adjacent faces


    Examples
    --------

    See examples/operations.enaml

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyOffsetShape)

    #: Create a solid from the resulting shape
    solid = d_(Bool(True))

    @observe("solid")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class ThickSolid(Offset):
    """An operation that creates a hollowed out solid from shape.

    Attributes
    ----------

    faces: List, optional
        List of faces that bound the solid.

    Examples
    --------

    ThickSolid:
        #: Creates an open box with a thickness of 0.1
        offset = 0.1
        Box: box:
            position = (4,-4,0)
        # Get top face
        faces << [sorted(box.topology.faces,key=top_face)[0]]

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyThickSolid)

    #: Closing faces
    faces = d_(List()).tag(view=True, group="ThickSolid")

    @observe("faces")
    def _update_proxy(self, change: dict[str, Any]):
        super(ThickSolid, self)._update_proxy(change)


class Pipe(Operation):
    """An operation that extrudes a profile along a spline, wire, or path.

    Attributes
    ----------

    spline: Edge or Wire
        The spline to extrude along.
    profile: Wire
        The profile to extrude.
    fill_mode: String, optional
        The fill mode to use.


    Examples
    --------

    See examples/pipes.enaml

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyPipe)

    #: Spline to make the pipe along
    spline = d_(Instance(object))

    #: Profile to make the pipe from
    profile = d_(Instance(object))

    #: Fill mode
    fill_mode = d_(
        Enum(
            None,
            "corrected_frenet",
            "fixed",
            "frenet",
            "constant_normal",
            "darboux",
            "guide_ac",
            "guide_plan",
            "guide_ac_contact",
            "guide_plan_contact",
            "discrete_trihedron",
        )
    ).tag(view=True, group="Pipe")

    @observe("spline", "profile", "fill_mode")
    def _update_proxy(self, change: dict[str, Any]):
        super(Pipe, self)._update_proxy(change)


class Evolved(Operation):
    """An operation that extrudes a profile along a spline, wire, or path.

    Attributes
    ----------

    spline: Edge or Wire
        The spline to extrude along.
    profile: Wire
        The profile to extrude.

    Examples
    --------

    See examples/evolved.enaml

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyEvolved)

    #: Spline to make the evolve along. It must be closed.
    spline = d_(Instance(object))

    #: Profile to make the evolved shaped from.
    #: This must be a planar Wire or Face.
    profile = d_(Instance(object))

    #: Run in parallel
    parallel = d_(Bool(True))

    #: Whether to fuse into a single solid or keep as a compound.
    solid = d_(Bool())

    #: Remove self-intersections in the result
    volume = d_(Bool())

    #: This axe prof flag
    global_axis = d_(Bool(True))

    # Whether the profile must be connected to the spline
    require_profile_on_spline = d_(Bool())

    #: Join type
    join_type = d_(Enum("arc", "tangent", "intersection"))

    @observe("spline", "profile", "join_type", "solid", "volume", "global_axis")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class AbstractRibSlot(Operation):
    #: Base shape
    shape = d_(Instance(Shape))

    #: Profile to make the pipe from
    contour = d_(Instance(Shape))

    #: Profile to make the pipe from
    plane = d_(Instance(Shape))

    #: Fuse (False to remove, True to add)
    fuse = d_(Bool(False)).tag(view=True)


class LinearForm(AbstractRibSlot):
    #: Reference to the implementation control
    proxy = Typed(ProxyLinearForm)

    #: Direction
    direction1 = d_(Instance((list, tuple))).tag(view=True)

    #: Modify
    modify = d_(Bool(False)).tag(view=True)


class RevolutionForm(AbstractRibSlot):
    #: Reference to the implementation control
    proxy = Typed(ProxyRevolutionForm)

    #: Height 1
    height1 = d_(Float(1.0, strict=False)).tag(view=True)

    #: Height 2
    height2 = d_(Float(1.0, strict=False)).tag(view=True)

    #: Sliding
    sliding = d_(Bool(False)).tag(view=True)


class DraftAngle(Operation):
    class Parameters(Atom):
        face = Instance((Shape, TopoDS_Shape))

        #: Angle relative to direction
        angle = Float(strict=False)

        #: Direction of the draft angle
        direction = Coerced(
            Direction, factory=lambda: Direction(0, 0, 1), coercer=coerce_direction
        )

        #: The point and direction of the neural plane
        neutral_plane = Tuple(Point, Direction)

    #: Reference to the implementation control
    proxy = Typed(ProxyDraftAngle)

    #: If True, don't apply the operation (for debugging)
    disabled = d_(Bool())

    #: Draft Angle
    angle = d_(Float(strict=False))

    #: List of faces to angle. Ignored if operations is given
    faces = d_(List())

    #: List of operations to perform. If this value is given all the
    #: other parameters are ignored.
    operations = d_(List(Parameters))

    @observe("faces", "angle", "operations", "disabled")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class ThruSections(Operation):
    """An operation that extrudes a shape by means of going through a series
     of profile sections along a spline or path.

    Attributes
    ----------

    solid: Bool
        If True, build a solid otherwise build a shell.
    ruled: Bool
        If False, smooth out the surfaces using approximation
    precision: Float, optional
        The precision to use for approximation.

    Examples
    --------

    See examples/thru_sections.enaml

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyThruSections)

    #: isSolid is set to true if the construction algorithm is required
    #: to build a solid or to false if it is required to build a shell
    #: (the default value),
    solid = d_(Bool(False)).tag(view=True, group="Through Sections")

    #: ruled is set to true if the faces generated between the edges
    #: of two consecutive wires are ruled surfaces or to false
    #: (the default value)
    #: if they are smoothed out by approximation
    ruled = d_(Bool(False)).tag(view=True, group="Through Sections")

    #: Apply shape fixing to the result
    fix = d_(Bool(False)).tag(view=True, group="Through Sections")

    #: pres3d defines the precision criterion used by the approximation
    #:  algorithm;
    #: the default value is 1.0e-6. Use AddWire and AddVertex to define
    #: the successive sections of the shell or solid to be built.
    precision = d_(Float(1e-6)).tag(view=True, group="Through Sections")

    #: List of sections to loft through
    sections = d_(List())

    @observe("solid", "ruled", "precision", "fix", "sections")
    def _update_proxy(self, change: dict[str, Any]):
        super(ThruSections, self)._update_proxy(change)


class TransformOperation(Atom):
    #: Point
    position = Coerced(Point, coercer=coerce_point)

    def _default_position(self) -> Point:
        return Point(0.0, 0.0, 0.0)


class Rotate(TransformOperation):
    #: Rotation axis
    direction = Coerced(Direction, coercer=coerce_direction)

    def _default_direction(self) -> Direction:
        return Direction(0.0, 0.0, 1.0)

    #: Angle
    angle = Float(0.0, strict=False)


class Translate(TransformOperation):
    #: Position
    x = Float(0.0, strict=False)
    y = Float(0.0, strict=False)
    z = Float(0.0, strict=False)

    def __init__(self, x: float = 0, y: float = 0, z: float = 0, **kwargs):
        super(Translate, self).__init__(x=x, y=y, z=z, **kwargs)


class Scale(TransformOperation):
    s = Float(1.0, strict=False)

    def __init__(self, s: float = 1, **kwargs):
        super(Scale, self).__init__(s=s, **kwargs)


class Mirror(TransformOperation):
    #: Position
    x = Float(0.0, strict=False)
    y = Float(0.0, strict=False)
    z = Float(0.0, strict=False)

    #: Mirror as plane
    plane = Bool()

    def __init__(self, x: float = 0, y: float = 0, z: float = 0, **kwargs):
        super(Mirror, self).__init__(x=x, y=y, z=z, **kwargs)


class Transform(Operation):
    """An operation that Transform's an existing shape (or a copy). If no
    operations are given it will align along the axis defined by the position
    direction and rotation.

    Attributes
    ----------

    shape: Shape or None
        Shape to transform. If none is given it will use the first child. If
        given it will make a transformed copy the reference shape.
    mirror: Tuple or List
        Mirror transformation to apply to the shape. Should be a list for each
        axis (True, False, True).
    scale: Tuple or List
        Scale to apply to the shape. Should be a list of float values
        for each axis ex. (2, 2, 2).
    rotate: Tuple or List
        Rotation to apply to the shape. Should be a list of float values
        (in radians) for each axis ex. (0, math.pi/2, 0).
    translate: Tuple or List
        Translation to apply to the shape. Should be a list of float values
        for each axis ex. (0, 0, 100).

    Examples
    --------

    Transform:
        operations = [Rotate(direction=(1, 0, 0), angle=math.pi/4)]
        Box: box:
            pass

    #: Or
    Cylinder: cyl
        pass

    Transform:
        #: Create a copy and move it
        shape = cyl
        operations = [
            Translate(x=10, y=20, z=0),
            Scale(s=2),
            Rotate(direction=(0,0,1), angle=math.pi/2)
        ]

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyTransform)

    #: Shape to transform
    #: if none is given the first child will be used
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: Transform ops
    operations = d_(List(TransformOperation))

    @observe("operations")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class Sew(Operation):
    #: Reference to the implementation control
    proxy = Typed(ProxySew)

    #: Convert resulting shell to a solid
    solid = d_(Bool())

    @observe("solid")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)

class Glue(Operation):
    #: Reference to the implementation control
    proxy = Typed(ProxyGlue)


class NormalProjection(Operation):
    """Project a wire onto a face. Requires at least one child shape. The
    result is a wire.

    """

    #: Reference to the implementation control
    proxy = Typed(ProxyNormalProjection)

    #: The face project onto
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: Max distance
    max_distance = d_(Float(strict=False))


class Extend(Operation):
    """Extend a curve or surface by it's parameters"""

    #: Reference to the implementation control
    proxy = Typed(ProxyExtend)

    #: The shape to extend.
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: How to interpret the parameters
    mode = d_(Enum("length", "parameter"))

    #: List of extend operations
    operations = d_(List())

    @observe("shape", "mode", "operations")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)


class RemoveFeatures(Operation):
    """Remove a feature from a shape."""

    #: Reference to the implementation control
    proxy = Typed(ProxyRemoveFeatures)

    #: The shape to remove features from. If not set it uses the first child.
    shape = d_(Instance((Shape, TopoDS_Shape)))

    #: If True, put all children in one operation otherwise
    #: perform a boolean operation with each child one at a time
    parallel = d_(Bool(False))

    #: Whether the operation should be disabled.
    disabled = d_(Bool(False))

    #: List of features to remove
    features = d_(List())

    @observe("shape", "features", "parallel", "disabled")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)
