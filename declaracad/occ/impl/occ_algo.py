"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import Int, Dict, Instance, Subclass, set_default
from enaml.application import timed_call

from OCCT.BOPAlgo import (
    BOPAlgo_Splitter, BOPAlgo_Section, BOPAlgo_MakeConnected
)
from OCCT.BRep import BRep_Builder
from OCCT.BRepAlgoAPI import (
    BRepAlgoAPI_BooleanOperation, BRepAlgoAPI_Fuse, BRepAlgoAPI_Common,
    BRepAlgoAPI_Cut
)
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_Transform, BRepBuilderAPI_MakeWire, BRepBuilderAPI_Sewing,
    BRepBuilderAPI_MakeSolid, BRepBuilderAPI_MakeFace
)
from OCCT.BRepFilletAPI import (
    BRepFilletAPI_MakeFillet, BRepFilletAPI_MakeChamfer,
    BRepFilletAPI_MakeFillet2d
)
from OCCT.BRepOffsetAPI import (
    BRepOffsetAPI_MakeOffset, BRepOffsetAPI_MakeOffsetShape,
    BRepOffsetAPI_MakeThickSolid, BRepOffsetAPI_MakePipe,
    BRepOffsetAPI_ThruSections, BRepOffsetAPI_DraftAngle
)
from OCCT.BRepOffset import (
    BRepOffset_Skin, BRepOffset_Pipe,
    BRepOffset_RectoVerso
)
from OCCT.BRepLib import BRepLib_FuseEdges
from OCCT.BRepTools import BRepTools
from OCCT.ChFi3d import (
    ChFi3d_Rational, ChFi3d_QuasiAngular, ChFi3d_Polynomial
)
from OCCT.GeomAbs import (
    GeomAbs_Arc, GeomAbs_Tangent, GeomAbs_Intersection
)
from OCCT.GeomFill import (
    GeomFill_IsCorrectedFrenet, GeomFill_IsFixed,
    GeomFill_IsFrenet, GeomFill_IsConstantNormal, GeomFill_IsDarboux,
    GeomFill_IsGuideAC, GeomFill_IsGuidePlan,
    GeomFill_IsGuideACWithContact, GeomFill_IsGuidePlanWithContact,
    GeomFill_IsDiscreteTrihedron
)
from OCCT.gp import (
    gp_Trsf, gp_Vec, gp_Pnt, gp_Ax1, gp_Ax2, gp_Ax3, gp_Dir, gp_Pnt2d, gp_Pln
)
from OCCT.ShapeAnalysis import ShapeAnalysis_FreeBounds
from OCCT.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.TColgp import TColgp_Array1OfPnt2d
from OCCT.TopTools import TopTools_ListOfShape, TopTools_HSequenceOfShape
from OCCT.TopoDS import (
    TopoDS, TopoDS_Edge, TopoDS_Face, TopoDS_Wire, TopoDS_Shape,
    TopoDS_Compound, TopoDS_Vertex
)


from declaracad.core.utils import log
from declaracad.occ.algo import (
    ProxyOperation, ProxyBooleanOperation, ProxyCommon, ProxyCut,
    ProxyDraftAngle, ProxyFuse, ProxyFillet, ProxyChamfer, ProxyOffset,
    ProxyOffsetShape, ProxyThickSolid, ProxyPipe, ProxyThruSections,
    ProxySplit, ProxyIntersection, ProxySew, ProxyGlue, ProxyTransform,
    Translate, Rotate, Scale, Mirror, Shape,
)

from .occ_shape import (
    OccShape, OccDependentShape, Topology, coerce_axis, coerce_shape
)


class OccOperation(OccDependentShape, ProxyOperation):
    """ Operation is a dependent shape that uses queuing to only
    perform the operation once all changes have settled because
    in general these operations are expensive.
    """
    def set_direction(self, direction):
        self.update_shape()

    def set_axis(self, axis):
        self.update_shape()


class OccBooleanOperation(OccOperation, ProxyBooleanOperation):
    """ Base class for a boolean shape operation.

    """
    op = Subclass(BRepAlgoAPI_BooleanOperation)

    def update_shape(self, change=None):
        op = self.op()
        d = self.declaration
        if d.shape1 and d.shape2:
            shape = self.op(coerce_shape(d.shape1),
                            coerce_shape(d.shape2)).Shape()
        else:
            shape = None

        for c in self.children():
            if shape is not None:
                shape = self.op(shape, c.shape).Shape()
            else:
                shape = c.shape

        if d.unify:
            tool = ShapeUpgrade_UnifySameDomain(shape)
            tool.Perform()
            shape = tool.Shape()

        if d.fix:
            fixer = ShapeFix_Shape(shape)
            if fixer.Perform():
                shape = fixer.Shape()

        self.shape = Topology.cast_shape(shape)


class OccCommon(OccBooleanOperation, ProxyCommon):
    """ Common of all the child shapes together. """
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_algo_a_p_i___common.html')
    op = set_default(BRepAlgoAPI_Common)


class OccCut(OccBooleanOperation, ProxyCut):
    """ Cut all the child shapes from the first shape. """
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_algo_a_p_i___cut.html')
    op = set_default(BRepAlgoAPI_Cut)


class OccFuse(OccBooleanOperation, ProxyFuse):
    """ Fuse all the child shapes together. """
    reference = set_default(
        'https://dev.opencascade.org/doc/overview/html/'
        'occt_user_guides__boolean_operations.html#occt_algorithms_7')
    op = set_default(BRepAlgoAPI_Fuse)


class OccIntersection(OccBooleanOperation, ProxyIntersection):
    reference = set_default(
        'https://dev.opencascade.org/doc/overview/html/'
        'occt_user_guides__boolean_operations.html#occt_algorithms_10a')

    def update_shape(self, change=None):
        section = BOPAlgo_Section()
        d = self.declaration
        if d.shape1:
            section.AddArgument(coerce_shape(d.shape1))
        if d.shape2:
            section.AddArgument(coerce_shape(d.shape2))
        for c in self.children():
            section.AddArgument(c.shape)
        section.Perform()
        if section.HasErrors():
            raise ValueError("Could not intersect shape %s" % d)
        self.shape = Topology.cast_shape(section.Shape())


class OccSplit(OccBooleanOperation, ProxySplit):
    """ Fuse all the child shapes together. """
    reference = set_default(
        'https://dev.opencascade.org/doc/overview/html/'
        'occt_user_guides__boolean_operations.html#occt_algorithms_8')

    def update_shape(self, change=None):
        splitter = BOPAlgo_Splitter()
        d = self.declaration
        tools = TopTools_ListOfShape()
        if d.shape1:
            shape = d.shape1
            splitter.AddArgument(shape)
        else:
            shape = None
        if d.shape2:
            tools.Append(d.shape2)
        for c in self.children():
            if shape:
                tools.Append(c.shape)
            else:
                shape = c.shape
                splitter.AddArgument(shape)
        splitter.SetTools(tools)
        splitter.Perform()
        if splitter.HasErrors():
            raise ValueError("Could not split shape %s" % d)
        self.shape = splitter.Shape()


class OccFillet(OccOperation, ProxyFillet):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_fillet_a_p_i___make_fillet.html')

    shape_types = {
        'rational': ChFi3d_Rational,
        'angular': ChFi3d_QuasiAngular,
        'polynomial': ChFi3d_Polynomial
    }

    def update_shape(self, change=None):
        d = self.declaration
        # Get the shape to apply the fillet to
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        s = child.shape
        if isinstance(s, (TopoDS_Wire, TopoDS_Face)):
            return self.fillet_2d(child)
        return self.fillet_3d(child)

    def fillet_2d(self, child):
        d = self.declaration
        shape = child.shape
        was_wire = isinstance(shape, TopoDS_Wire)
        if was_wire:
            shape = BRepBuilderAPI_MakeFace(shape).Face()
        fillet = BRepFilletAPI_MakeFillet2d(shape)
        operations = d.operations if d.operations else child.topology.vertices
        for item in operations:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                r, v = item
                fillet.AddFillet(v, r)
            elif isinstance(item, TopoDS_Vertex):
                fillet.AddFillet(item, d.radius)
            else:
                log.warning(f"Invalid fillet {item}")

        shape = Topology.cast_shape(fillet.Shape())
        if was_wire:
            shape = BRepTools.OuterWire_(shape)
        self.shape = shape

    def fillet_3d(self, child):
        d = self.declaration
        fillet = BRepFilletAPI_MakeFillet(child.shape)
        operations = d.operations if d.operations else child.topology.edges
        for item in operations:
            if not isinstance(item, (list, tuple)):
                r = d.radius
                if isinstance(item, TopoDS_Face):
                    for edge in Topology(shape=item).edges_from_face(item):
                        fillet.Add(r, edge)
                else:
                    fillet.Add(r, item)
                continue

            # If an array of points is create a changing radius fillet
            n = len(item)
            if n == 2 and isinstance(item[0], (list, tuple)):
                pts, edge = item
                array = TColgp_Array1OfPnt2d(1, len(pts))
                for i, pt in enumerate(pts):
                    array.SetValue(i+1, gp_Pnt2d(*pt))
                fillet.Add(array, edge)
                continue
            if n == 2 and isinstance(item[1], TopoDS_Face):
                r, face = item
                for edge in Topology(shape=face).edges_from_face(face):
                    fillet.Add(r, edge)
                continue
            # custom radius or r1 and r2 radius fillets
            fillet.Add(*item)
        self.shape = fillet.Shape()

    def set_shape_type(self, shape_type):
        self.update_shape()

    def set_radius(self, r):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()


class OccChamfer(OccOperation, ProxyChamfer):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_fillet_a_p_i___make_chamfer.html')

    def update_shape(self, change=None):
        d = self.declaration

        #: Get the shape to apply the fillet to
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        chamfer = BRepFilletAPI_MakeChamfer(child.shape)

        operations = d.operations if d.operations else child.topology.faces

        for item in operations:
            edge = None
            d1, d2 = d.distance, d.distance2 or d.distance
            if isinstance(item, (tuple, list)):
                face = item[-1]
                n = len(item)
                if n > 1:
                    i = 0
                    if isinstance(item[-2], TopoDS_Edge):
                        edge = item[-2]
                        i += 1
                    if n == i + 2:
                        d1 = d2 = item[0]
                    elif n == i + 3:
                        d1, d2 = item[0:2]
            else:
                face = item

            if isinstance(face, TopoDS_Edge) and d1 == d2:
                edge = face
                chamfer.Add(d1, edge)
            elif edge is None:
                for edge in child.topology.edges_from_face(face):
                    chamfer.Add(d1, d2, edge, face)
            else:
                chamfer.Add(d1, d2, edge, face)
        self.shape = chamfer.Shape()

    def set_distance(self, d):
        self.update_shape()

    def set_distance2(self, d):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()


class OccOffset(OccOperation, ProxyOffset):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___make_offset.html')

    offset_modes = {
        'skin': BRepOffset_Skin,
        'pipe': BRepOffset_Pipe,
        'recto_verso': BRepOffset_RectoVerso
    }

    join_types = {
        'arc': GeomAbs_Arc,
        'tangent': GeomAbs_Tangent,
        'intersection': GeomAbs_Intersection,
    }

    def get_shape_to_offset(self):
        d = self.declaration
        if d.shape:
            return coerce_shape(d.shape)
        return self.get_first_child().shape

    def update_shape(self, change=None):
        d = self.declaration
        shape = Topology.cast_shape(self.get_shape_to_offset())
        if isinstance(shape, TopoDS_Edge):
            shape = BRepBuilderAPI_MakeWire(shape).Wire()
        elif not isinstance(shape, (TopoDS_Wire, TopoDS_Face)):
            t = type(shape)
            raise TypeError(
                "Unsupported child shape %s when using planar mode" % t)
        join_type = self.join_types[d.join_type]
        offset_shape = BRepOffsetAPI_MakeOffset(shape, join_type, not d.closed)
        offset_shape.Perform(d.offset, d.normal_distance)
        if not offset_shape.IsDone():
            # Note: Lines cannot be offset as they have no plane of reference
            raise ValueError("Could not perform offset: %s" % d)
        self.shape = Topology.cast_shape(offset_shape.Shape())

    def set_shape(self, shape):
        self.update_shape()

    def set_offset(self, offset):
        self.update_shape()

    def set_offset_mode(self, mode):
        self.update_shape()

    def set_join_type(self, mode):
        self.update_shape()

    def set_intersection(self, enabled):
        self.update_shape()


class OccOffsetShape(OccOffset, ProxyOffsetShape):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___make_offset_shape.html')

    def update_shape(self, change=None):
        d = self.declaration
        shape = self.get_shape_to_offset()
        offset_shape = BRepOffsetAPI_MakeOffsetShape()
        offset_shape.PerformByJoin(
            shape,
            d.offset,
            d.tolerance,
            self.offset_modes[d.offset_mode],
            d.intersection,
            False,
            self.join_types[d.join_type]
        )
        self.shape = offset_shape.Shape()


class OccThickSolid(OccOffset, ProxyThickSolid):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___make_thick_solid.html')

    def get_faces(self, occ_shape):
        d = self.declaration
        if d.faces:
            return d.faces

        if isinstance(occ_shape, TopoDS_Shape):
            topology = Topology(shape=occ_shape)
        else:
            topology = occ_shape.topology

        for face in topology.faces:
            return [face]

    def update_shape(self, change=None):
        d = self.declaration
        shape = self.get_shape_to_offset()
        faces = TopTools_ListOfShape()
        for f in self.get_faces(shape):
            faces.Append(f)
        assert not faces.IsEmpty()

        offset_mode = self.offset_modes[d.offset_mode]
        join_type = self.join_types[d.join_type]

        thick_solid = BRepOffsetAPI_MakeThickSolid()
        thick_solid.MakeThickSolidByJoin(
            shape,
            faces,
            d.offset,
            d.tolerance,
            offset_mode,
            d.intersection,
            False,
            join_type,
        )
        self.shape = thick_solid.Shape()

    def set_faces(self, faces):
        self.update_shape()


class OccPipe(OccOperation, ProxyPipe):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___make_pipe.html')

    #: References to observed shapes
    _old_spline = Instance(OccShape)
    _old_profile = Instance(OccShape)

    fill_modes = {
        'corrected_frenet': GeomFill_IsCorrectedFrenet,
        'fixed': GeomFill_IsFixed,
        'frenet': GeomFill_IsFrenet,
        'constant_normal': GeomFill_IsConstantNormal,
        'darboux': GeomFill_IsDarboux,
        'guide_ac': GeomFill_IsGuideAC,
        'guide_plan': GeomFill_IsGuidePlan,
        'guide_ac_contact': GeomFill_IsGuideACWithContact,
        'guide_plan_contact': GeomFill_IsGuidePlanWithContact,
        'discrete_trihedron': GeomFill_IsDiscreteTrihedron
    }

    def update_shape(self, change=None):
        d = self.declaration

        if d.spline and d.profile:
            spline, profile = d.spline, d.profile
        elif d.spline:
            spline = d.spline
            profile = self.get_first_child().shape
        elif d.profile:
            profile = d.profile
            spline = self.get_first_child().shape
        else:
            shapes = [c.shape for c in self.children() if isinstance(c, OccShape)]
            spline, profile = shapes[0:2]

        args = [coerce_shape(spline), coerce_shape(profile)]

        # Make sure spline is a wire
        if isinstance(args[0], TopoDS_Edge):
            args[0] = BRepBuilderAPI_MakeWire(args[0]).Wire()

        if d.fill_mode:
            args.append(self.fill_modes[d.fill_mode])
        pipe = BRepOffsetAPI_MakePipe(*args)
        self.shape = pipe.Shape()

    def set_spline(self, spline):
        self.update_shape()

    def set_profile(self, profile):
        self.update_shape()

    def set_fill_mode(self, mode):
        self.update_shape()


class OccThruSections(OccOperation, ProxyThruSections):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'class_b_rep_offset_a_p_i___thru_sections.html')

    def update_shape(self, change=None):
        from .occ_draw import OccVertex, OccWire

        d = self.declaration
        loft = BRepOffsetAPI_ThruSections(d.solid, d.ruled, d.precision)
        #loft.CheckCompatibility(True)
        #: TODO: Support Smoothing, Max degree, par type, etc...

        for child in self.children():
            s = child.shape
            if isinstance(s, TopoDS_Vertex):
                loft.AddVertex(s)
            elif isinstance(s, TopoDS_Edge):
                loft.AddWire(BRepBuilderAPI_MakeWire(s).Wire())
            elif isinstance(s, TopoDS_Wire):
                loft.AddWire(s)

        #: Set the shape
        self.shape = loft.Shape()

    def set_solid(self, solid):
        self.update_shape()

    def set_ruled(self, ruled):
        self.update_shape()

    def set_precision(self, pres3d):
        self.update_shape()


class OccTransform(OccOperation, ProxyTransform):
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___trsf.html')

    _old_shape = Instance(OccShape)

    def get_transform(self):
        d = self.declaration
        result = gp_Trsf()
        #: TODO: Order matters... how to configure it???
        if d.operations:
            for op in d.operations:
                t = gp_Trsf()
                if isinstance(op, Translate):
                    t.SetTranslation(gp_Vec(op.x, op.y, op.z))
                elif isinstance(op, Rotate):
                    t.SetRotation(gp_Ax1(gp_Pnt(*op.point),
                                        gp_Dir(*op.direction)), op.angle)
                elif isinstance(op, Mirror):
                    Ax = gp_Ax2 if op.plane else gp_Ax1
                    t.SetMirror(Ax(gp_Pnt(*op.point),
                                   gp_Dir(op.x, op.y, op.z)))
                elif isinstance(op, Scale):
                    t.SetScale(gp_Pnt(*op.point), op.s)
                result.Multiply(t)
        else:
            axis = gp_Ax3()
            axis.SetDirection(d.direction.proxy)
            result.SetTransformation(axis)
            result.SetTranslationPart(gp_Vec(*d.position))
            if d.rotation:
                t = gp_Trsf()
                t.SetRotation(gp_Ax1(d.position.proxy, d.direction.proxy),
                              d.rotation)
                result.Multiply(t)

        return result

    def update_shape(self, change=None):
        d = self.declaration

        #: Get the shape to apply the tranform to
        if d.shape:
            original = coerce_shape(d.shape)
        else:
            # Use the first child
            child = self.get_first_child()
            if child is None:
                raise ValueError(
                    "Transform has no shape to transform %s" % d)
            original = child.shape

        t = self.get_transform()
        transform = BRepBuilderAPI_Transform(original, t, True)
        shape = transform.Shape()

        # Convert it back to the original type
        self.shape = Topology.cast_shape(shape)

    def set_shape(self, shape):
        if self._old_shape:
            self._old_shape.unobserve('shape', self.update_shape)
        self._old_shape = shape.proxy
        self._old_shape.observe('shape', self.update_shape)

    def set_translate(self, translation):
        self.update_shape()

    def set_rotate(self, rotation):
        self.update_shape()

    def set_scale(self, scale):
        self.update_shape()

    def set_mirror(self, axis):
        self.update_shape()


class OccSew(OccOperation, ProxySew):
    def update_shape(self, change=None):
        d = self.declaration
        builder = BRepBuilderAPI_Sewing()
        for s in self.child_shapes():
            builder.Add(Topology.cast_shape(s))
        builder.Perform()
        self.shape = Topology.cast_shape(builder.SewedShape())


class OccGlue(OccOperation, ProxyGlue):
    def update_shape(self, change=None):
        d = self.declaration
        raise NotImplementedError  # TODO: This


class OccDraftAngle(OccOperation, ProxyDraftAngle):
    def update_shape(self, change=None):
        d = self.declaration
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        draft = BRepOffsetAPI_DraftAngle(child.shape)

        if d.operations:
            for op in d.operations:
                pln_pos, pln_dir = op.neutral_plane
                neutral_plane = gp_Pln(pln_pos.proxy, pln_dir.proxy)
                draft.Add(op.face, op.direction.proxy, op.angle, neutral_plane)
        else:
            a = d.angle
            neutral_plane = gp_Pln(d.position.proxy, d.direction.proxy)
            for f in d.faces:
                draft.Add(f, d.direction.proxy, a, neutral_plane)

        draft.Build()
        if not draft.IsDone():
            raise RuntimeError(f"Could not build draft {d}")
        self.shape = draft.Shape()

    def set_disabled(self, disabled):
        self.update_shape()

    def set_angle(self, angle):
        self.update_shape()

    def set_faces(self, faces):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()
