"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
import os
from math import pi
from typing import Union, Tuple as TupleType
from atom.api import (
    Atom,
    Bool,
    Instance,
    List,
    Typed,
    Str,
    Property,
    observe,
    set_default,
)

from OCCT.AIS import AIS_Shape, AIS_TexturedShape, AIS_MultipleConnectedInteractive
from OCCT.Bnd import Bnd_Box
from OCCT.BRep import BRep_Builder
from OCCT.BRepBndLib import BRepBndLib
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeShape,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_Transform,
    BRepBuilderAPI_MakeWire,
)
from OCCT.BRepPrimAPI import (
    BRepPrimAPI_MakeBox,
    BRepPrimAPI_MakeCone,
    BRepPrimAPI_MakeCylinder,
    BRepPrimAPI_MakeHalfSpace,
    BRepPrimAPI_MakePrism,
    BRepPrimAPI_MakeSphere,
    BRepPrimAPI_MakeWedge,
    BRepPrimAPI_MakeTorus,
    BRepPrimAPI_MakeRevol,
)

from OCCT.gp import gp, gp_Pnt, gp_Dir, gp_Vec, gp_Ax1, gp_Ax2, gp_Ax3, gp_Trsf, gp_Pln
from OCCT.TopoDS import (
    TopoDS,
    TopoDS_Wire,
    TopoDS_Vertex,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Compound,
    TopoDS_CompSolid,
    TopoDS_Shape,
    TopoDS_Iterator,
)
from OCCT.TopLoc import TopLoc_Location
from OCCT.TCollection import TCollection_AsciiString
from OCCT.TDF import TDF_Label

from declaracad.occ.shape import (
    ProxyShape,
    ProxyPart,
    ProxyFace,
    ProxyBox,
    ProxyCone,
    ProxyCylinder,
    ProxyHalfSpace,
    ProxyPrism,
    ProxySphere,
    ProxyWedge,
    ProxyRawPart,
    ProxyTorus,
    ProxyRevol,
    ProxyRawShape,
    ProxyLoadShape,
    BBox,
    Shape,
    Point,
    Direction,
    coerce_point,
    coerce_direction,
)

from declaracad.occ.algo import Translate, Rotate, Scale, Mirror

from .utils import color_to_quantity_color, material_to_material_aspect
from .topology import Topology

from declaracad.core.utils import log


DX = gp_Dir(1, 0, 0)
DXN = gp_Dir(-1, 0, 0)
DY = gp_Dir(0, 1, 0)
DYN = gp_Dir(0, -1, 0)
DZ = gp_Dir(0, 0, 1)
DZN = gp_Dir(0, 0, -1)
AX = gp_Ax1()
AX.SetDirection(gp.DX_())
AY = gp_Ax1()
AY.SetDirection(gp.DY_())
AZ = gp_Ax1()
AZ.SetDirection(gp.DZ_())


def coerce_axis(value: TupleType[Point, Direction, float]) -> gp_Ax2:
    pos, dir, rotation = value
    axis = gp_Ax2(pos.proxy, dir.proxy)
    axis.Rotate(axis.Axis(), rotation)
    return axis


def coerce_shape(shape: Union[TopoDS_Shape, Shape]) -> TopoDS_Shape:
    """Coerce a declaration into a TopoDS_Shape"""
    if isinstance(shape, Shape):
        return shape.proxy.shape
    return shape


class OccShape(ProxyShape):
    #: A reference to the toolkit shape created by the proxy.
    shape = Typed(TopoDS_Shape)

    #: The shape that was shown on the screen
    ais_shape = Instance(AIS_Shape)

    #: The XCAF application label
    tdf_label = Instance(TDF_Label)

    #: Whether this is currently displayed
    displayed = Bool()

    #: Topology explorer of the shape
    topology = Typed(Topology)

    #: Class reference url
    reference = Str()

    #: Cached reference to the viewer
    def _get_viewer(self):
        parent = self.parent()
        if isinstance(parent, OccShape):
            return parent.viewer
        return parent

    viewer = Property(_get_viewer, cached=True)

    location = Typed(TopLoc_Location)

    # -------------------------------------------------------------------------
    # Initialization API
    # -------------------------------------------------------------------------
    def create_shape(self):
        """Create the toolkit shape for the proxy object.

        This method is called during the top-down pass, just before the
        'init_shape()' method is called. This method should create the
        toolkit widget and assign it to the 'widget' attribute.

        """
        raise NotImplementedError

    def init_shape(self):
        """Initialize the state of the toolkit widget.

        This method is called during the top-down pass, just after the
        'create_widget()' method is called. This method should init the
        state of the widget. The child widgets will not yet be created.

        """
        pass

    def init_layout(self):
        """Initialize the layout of the toolkit shape."""
        pass

    def activate_top_down(self):
        """Activate the proxy for the top-down pass."""
        self.create_shape()
        self.init_shape()

    def activate_bottom_up(self):
        """Activate the proxy tree for the bottom-up pass."""
        self.init_layout()

    # -------------------------------------------------------------------------
    # Defaults and Observers
    # -------------------------------------------------------------------------
    def _default_topology(self):
        if self.shape is None:
            self.declaration.render()  # Force build the shape
        return Topology(shape=self.shape)

    def _observe_displayed(self, change):
        if self.displayed:
            parent = self.parent()
            if isinstance(parent, OccShape):
                parent.displayed = True

    @observe("shape")
    def on_shape_changed(self, change):
        if self.shape is not None:
            self.topology = self._default_topology()
        if self.displayed:
            self.ais_shape = self._default_ais_shape()

    def get_first_child(self):
        """Return shape to apply the operation to."""
        for child in self.children():
            if isinstance(child, OccShape):
                return child

    def child_shapes(self):
        """Iterator of all child shapes"""
        for child in self.children():
            if isinstance(child, OccShape):
                if hasattr(child, "shapes"):
                    for s in child.shapes:
                        yield s
                else:
                    yield child.shape

    def walk_shapes(self):
        """Iterator of all child shapes"""
        if not self.declaration.display:
            return
        if isinstance(self, OccPart):
            for s in self.children():
                if isinstance(s, OccShape):
                    yield from s.walk_shapes()
        else:
            yield self

    def _default_ais_shape(self):
        """Generate the AIS shape for the viewer to display.
        This is only invoked when the viewer wants to display the shape.

        """
        d = self.declaration

        if d.texture is not None:
            texture = d.texture
            ais_shape = AIS_TexturedShape(self.shape)

            if os.path.exists(texture.path):
                path = TCollection_AsciiString(texture.path)
                ais_shape.SetTextureFileName(path)
                params = texture.repeat
                ais_shape.SetTextureRepeat(params.enabled, params.u, params.v)
                params = texture.origin
                ais_shape.SetTextureOrigin(params.enabled, params.u, params.v)
                params = texture.scale
                ais_shape.SetTextureScale(params.enabled, params.u, params.v)
                ais_shape.SetTextureMapOn()
                ais_shape.SetDisplayMode(3)
        else:
            ais_shape = AIS_Shape(self.shape)

        ais_shape.SetTransparency(d.transparency)
        if d.material.name:
            ma = material_to_material_aspect(d.material)
            ais_shape.SetMaterial(ma)
        if d.color:
            c, a = color_to_quantity_color(d.color)
            ais_shape.SetColor(c)
            if a is not None:
                ais_shape.SetTransparency(a)

        ais_shape.SetLocalTransformation(self.location.Transformation())
        return ais_shape

    def _default_location(self):
        """Get the final location based on the assembly tree."""
        location = TopLoc_Location()
        parent = self.parent()
        while isinstance(parent, OccPart):
            location = parent.location.Multiplied(location)
            parent = parent.parent()
        return location

    # -------------------------------------------------------------------------
    # Proxy API
    # -------------------------------------------------------------------------
    def get_transform(self):
        """Create a transform which rotates the default axis to align
        with the normal given by the position

        Returns
        -------
        transform: gp_Trsf

        """
        d = self.declaration

        # Move to position and align along direction axis
        t = gp_Trsf()
        if d.direction.is_parallel(DZ):
            t.SetRotation(AZ, d.direction.angle(DZ) + d.rotation)
        else:
            d1 = d.direction.cross(DZ)
            axis = gp_Ax1(gp_Pnt(0, 0, 0), d1.proxy)
            t.SetRotation(axis, d.direction.angle(DZ))

            # Apply the rotation an reverse any rotation added in
            sign = 1 if d1.y >= 0 else -1
            angle = d.rotation + sign * d1.angle(DX)

            if angle:
                rot = gp_Trsf()
                rot.SetRotation(AZ, angle)
                t.Multiply(rot)

        t.SetTranslationPart(gp_Vec(*d.position))
        return t

    def set_position(self, position):
        self.create_shape()

    def set_direction(self, direction):
        self.create_shape()

    def set_axis(self, axis):
        self.create_shape()

    def parent_shape(self):
        p = self.parent()
        if p is not None:
            return p.shape

    def get_bounding_box(self, shape=None):
        shape = shape or self.shape
        if not shape:
            return BBox()
        bbox = Bnd_Box()
        BRepBndLib.Add_(shape, bbox)
        pmin, pmax = bbox.CornerMin(), bbox.CornerMax()
        return BBox(*(pmin.X(), pmin.Y(), pmin.Z(), pmax.X(), pmax.Y(), pmax.Z()))


class OccDependentShape(OccShape):
    """Shape that is dependent on another shape"""

    def create_shape(self):
        """Create the toolkit shape for the proxy object.

        Operations depend on child or properties so they cannot be created
        in the top down pass but rather must be done in the init_layout method.

        """
        pass

    def init_layout(self):
        """Initialize the layout of the toolkit shape.

        This method is called during the bottom-up pass. This method
        should initialize the layout of the widget. The child widgets
        will be fully initialized and layed out when this is called.

        """
        try:
            self.update_shape()
        except Exception as e:
            log.exception(e)
            raise e
        # log.debug('init_layout %s shape %s' % (self, self.shape))
        assert self.shape is not None, "Shape was not created %s" % self

        # When they change re-compute
        for child in self.children():
            child.observe("shape", self.update_shape)

    def update_shape(self, change=None):
        """Must be implmented in subclasses to create the shape
        when the dependent shapes change.
        """
        raise NotImplementedError

    def child_added(self, child):
        super().child_added(child)
        if isinstance(child, OccShape):
            child.observe("shape", self.update_shape)
            if self.displayed and self.viewer:
                self.viewer.add_shape_to_display(child)

    def child_removed(self, child):
        super().child_removed(child)
        if isinstance(child, OccShape):
            child.unobserve("shape", self.update_shape)
            if child.displayed and self.viewer:
                self.viewer.remove_shape_from_display(child)

    def set_direction(self, direction):
        self.update_shape()

    def set_axis(self, axis):
        self.update_shape()


class OccPart(OccDependentShape, ProxyPart):
    #: A reference to the toolkit shape created by the proxy.
    builder = Typed(BRep_Builder, ())

    #: Location
    location = Typed(TopLoc_Location)

    #: Display each sub-item
    ais_shape = Typed(AIS_MultipleConnectedInteractive)

    def get_transform(self) -> gp_Trsf:
        """Compute the transform for locating the part.

        This factors in the transforms applied to the part as well as the
        position, direction and rotation attributes.

        """
        result = super().get_transform()
        d = self.declaration
        for op in d.transform:
            t = gp_Trsf()
            if isinstance(op, Translate):
                t.SetTranslation(gp_Vec(op.x, op.y, op.z))
            elif isinstance(op, Rotate):
                t.SetRotation(
                    gp_Ax1(gp_Pnt(*op.point), gp_Dir(*op.direction)), op.angle
                )
            elif isinstance(op, Mirror):
                Ax = gp_Ax2 if op.plane else gp_Ax1
                t.SetMirror(Ax(gp_Pnt(*op.point), gp_Dir(op.x, op.y, op.z)))
            elif isinstance(op, Scale):
                t.SetScale(gp_Pnt(*op.point), op.s)
            result.Multiply(t)
        return result

    def _default_location(self) -> TopLoc_Location:
        """Set the location of this part based on the transformation."""
        return TopLoc_Location(self.get_transform())

    def _default_ais_shape(self) -> AIS_MultipleConnectedInteractive:
        ais_obj = AIS_MultipleConnectedInteractive()
        viewer = self.viewer
        ais_context = viewer.ais_context
        for c in self.children():
            if isinstance(c, OccShape):
                # HACK: WTF???
                if ais_context.IsDisplayed(c.ais_shape):
                    viewer.remove_shape_from_display(c)
                    ais_obj.Connect(c.ais_shape)
                    viewer.add_shape_to_display(c)
                else:
                    ais_obj.Connect(c.ais_shape)

        ais_obj.SetLocalTransformation(self.location.Transformation())
        return ais_obj

    def update_shape(self, change=None):
        """Create the toolkit shape for the proxy object."""
        d = self.declaration
        builder = self.builder
        shape = TopoDS_Compound()
        builder.MakeCompound(shape)
        for c in self.children():
            if not isinstance(c, OccShape):
                continue
            if c.shape is None or not c.declaration.display:
                continue
            # Note infinite planes cannot be added to a compound!
            builder.Add(shape, c.shape)
        location = self.location = self._default_location()
        shape.Location(location)
        self.shape = shape

    def update_location(self, change=None):
        """Recompute the location of this and all nested parts.

        This only updates the viewer.

        """
        new_location = self.location = self._default_location()
        ais_shape = self.ais_shape
        viewer = self.viewer

        # Recompute locations
        for c in self.walk_shapes():
            loc = c.location = c._default_location()
            viewer.ais_context.SetLocation(c.ais_shape, loc)
        viewer.update()

    def set_position(self, position):
        self.update_location()

    def set_direction(self, direction):
        self.update_location()

    def set_rotation(self, rotation):
        self.update_location()

    def set_transform(self, ops):
        self.update_location()


class OccFace(OccDependentShape, ProxyFace):
    def set_wires(self, wires):
        self.update_shape()

    def shape_to_face(self, shape):
        if isinstance(shape, OccShape):
            shape = shape.shape
        shape = Topology.cast_shape(shape)
        if isinstance(shape, (TopoDS_Face, TopoDS_Wire)):
            return shape
        if isinstance(shape, TopoDS_Edge):
            return BRepBuilderAPI_MakeWire(shape).Wire()
        return TopoDS.Wire_(shape)

    def update_shape(self, change=None):
        d = self.declaration
        if d.wires:
            shapes = d.wires
        else:
            shapes = [c for c in self.children() if isinstance(c, OccShape)]
        if not shapes:
            raise ValueError("No wires or children available to create a face!")

        convert = self.shape_to_face
        for i, s in enumerate(shapes):
            if i == 0:
                shape = BRepBuilderAPI_MakeFace(convert(s))
            else:
                shape.Add(convert(s))
        self.shape = shape.Face()


class OccBox(OccShape, ProxyBox):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_box.html"
    )

    def create_shape(self):
        d = self.declaration
        box = BRepPrimAPI_MakeBox(coerce_axis(d.axis), d.dx, d.dy, d.dz)
        self.shape = box.Shape()

    def set_dx(self, dx):
        self.create_shape()

    def set_dy(self, dy):
        self.create_shape()

    def set_dz(self, dz):
        self.create_shape()


class OccCone(OccShape, ProxyCone):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_cone.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.radius2, d.height]
        if d.angle:
            args.append(d.angle)
        cone = BRepPrimAPI_MakeCone(*args)
        self.shape = cone.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_height(self, height):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()


class OccCylinder(OccShape, ProxyCylinder):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_cylinder.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.height]
        if d.angle:
            args.append(d.angle)
        cylinder = BRepPrimAPI_MakeCylinder(*args)
        self.shape = cylinder.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_angle(self, angle):
        self.create_shape()

    def set_height(self, height):
        self.create_shape()


class OccHalfSpace(OccDependentShape, ProxyHalfSpace):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_half_space.html"
    )

    def update_shape(self, change=None):
        d = self.declaration
        if d.surface:
            surface = d.surface
        else:
            child = self.get_first_child()
            if child:
                surface = child.shape
            else:
                pln = gp_Pln(d.position.proxy, d.direction.proxy)
                surface = BRepBuilderAPI_MakeFace(pln).Face()
        half_space = BRepPrimAPI_MakeHalfSpace(surface, d.side.proxy)
        # Shape doesnt work see
        # https://tracker.dev.opencascade.org/view.php?id=29969
        self.shape = half_space.Solid()

    def set_surface(self, surface):
        self.update_shape()

    def set_side(self, side):
        self.update_shape()


class OccPrism(OccDependentShape, ProxyPrism):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_prism.html"
    )

    def update_shape(self, change=None):
        d = self.declaration

        if d.shape:
            shape = coerce_shape(d.shape)
            copy = True
        else:

            shape = self.get_shape().shape
            copy = False

        if d.infinite:
            args = (shape, d.direction.proxy, True, copy, d.canonize)
        else:
            args = (shape, gp_Vec(*d.vector), copy, d.canonize)
        prism = BRepPrimAPI_MakePrism(*args)
        self.shape = prism.Shape()

    def get_shape(self):
        for child in self.children():
            if isinstance(child, OccShape):
                return child

    def set_shape(self, shape):
        self.update_shape()

    def set_infinite(self, infinite):
        self.update_shape()

    def set_copy(self, copy):
        self.update_shape()

    def set_canonize(self, canonize):
        self.update_shape()

    def set_direction(self, direction):
        self.update_shape()

    def set_vector(self, vector):
        self.update_shape()


class OccRevol(OccDependentShape, ProxyRevol):

    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_wedge.html"
    )

    def update_shape(self, change=None):
        d = self.declaration

        if d.shape:
            shape = coerce_shape(d.shape)
            copy = True
        else:
            shape = self.get_shape().shape
            copy = False

        #: Build arguments
        args = [shape, gp_Ax1(d.position.proxy, d.direction.proxy)]
        if d.angle:
            args.append(d.angle)
        args.append(copy)
        revol = BRepPrimAPI_MakeRevol(*args)
        self.shape = revol.Shape()

    def get_shape(self):
        """Get the first child shape"""
        for child in self.children():
            if isinstance(child, OccShape):
                return child

    def set_shape(self, shape):
        self.update_shape()

    def set_angle(self, angle):
        self.update_shape()

    def set_copy(self, copy):
        self.update_shape()

    def set_direction(self, direction):
        self.update_shape()


class OccSphere(OccShape, ProxySphere):
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_sphere.html"
    )

    def create_shape(self):
        d = self.declaration
        u = min(2 * pi, max(0, d.angle))
        vmin = max(-pi / 2, min(d.angle2, d.angle3))
        vmax = min(pi / 2, max(d.angle2, d.angle3))
        sphere = BRepPrimAPI_MakeSphere(coerce_axis(d.axis), d.radius, vmin, vmax, u)
        self.shape = sphere.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()

    def set_angle2(self, a):
        self.create_shape()

    def set_angle3(self, a):
        self.create_shape()


class OccTorus(OccShape, ProxyTorus):

    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_torus.html"
    )

    def create_shape(self):
        d = self.declaration
        args = [coerce_axis(d.axis), d.radius, d.radius2]
        if d.angle2 or d.angle3:
            amin = min(d.angle2, d.angle3)
            amax = max(d.angle2, d.angle3)
            args.append(amin)
            args.append(amax)
        if d.angle:
            args.append(d.angle)
        torus = BRepPrimAPI_MakeTorus(*args)
        self.shape = torus.Shape()

    def set_radius(self, r):
        self.create_shape()

    def set_radius2(self, r):
        self.create_shape()

    def set_angle(self, a):
        self.create_shape()

    def set_angle2(self, a):
        self.create_shape()

    def set_angle3(self, a):
        self.create_shape()


class OccWedge(OccShape, ProxyWedge):

    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_prim_a_p_i___make_wedge.html"
    )

    def create_shape(self):
        d = self.declaration
        wedge = BRepPrimAPI_MakeWedge(coerce_axis(d.axis), d.dx, d.dy, d.dz, d.itx)
        self.shape = wedge.Shape()

    def set_dx(self, dx):
        self.create_shape()

    def set_dy(self, dy):
        self.create_shape()

    def set_dz(self, dz):
        self.create_shape()

    def set_itx(self, itx):
        self.create_shape()


class OccRawShape(OccShape, ProxyRawShape):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/" "class_topo_d_s___shape.html"
    )

    def create_shape(self):
        """Delegate shape creation to the declaration implementation."""
        self.shape = self.declaration.create_shape(self.parent_shape())

    # -------------------------------------------------------------------------
    # ProxyRawShape API
    # -------------------------------------------------------------------------
    def get_shape(self):
        """Retrieve the underlying toolkit shape."""
        return self.shape


class OccRawPart(OccPart, ProxyRawPart):
    #: Update the class reference
    reference = set_default(
        "https://dev.opencascade.org/doc/refman/html/" "class_topo_d_s___shape.html"
    )

    shapes = List(TopoDS_Shape)

    def create_shapes(self):
        """Delegate shape creation to the declaration implementation."""
        self.shapes = self.declaration.create_shapes(self.parent_shape())

    # -------------------------------------------------------------------------
    # ProxyRawShape API
    # -------------------------------------------------------------------------
    def get_shapes(self):
        """Retrieve the underlying toolkit shape."""
        return self.shapes
