"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Atom, Instance, Typed, Bool, List

from OCCT import GeomAbs
from OCCT.BOPAlgo import BOPAlgo_Section
from OCCT.Bnd import Bnd_Box
from OCCT.BRepAdaptor import (
    BRepAdaptor_Curve, BRepAdaptor_CompCurve, BRepAdaptor_Surface
)
from OCCT.BRepBndLib import BRepBndLib
from OCCT.BRepTools import BRepTools_WireExplorer
from OCCT.BRepGProp import BRepGProp
from OCCT.GC import GC_MakeSegment
from OCCT.GCPnts import (
    GCPnts_UniformDeflection, GCPnts_QuasiUniformDeflection,
    GCPnts_UniformAbscissa, GCPnts_QuasiUniformAbscissa
)
from OCCT.Geom import (
    Geom_Ellipse, Geom_Circle, Geom_Parabola, Geom_Hyperbola, Geom_Line,
    Geom_TrimmedCurve
)
from OCCT.GeomAbs import (
    GeomAbs_Line, GeomAbs_Circle, GeomAbs_Ellipse, GeomAbs_Hyperbola,
    GeomAbs_Parabola, GeomAbs_BezierCurve, GeomAbs_BSplineCurve,
    GeomAbs_OffsetCurve, GeomAbs_OtherCurve, GeomAbs_Cylinder
)
from OCCT.GProp import GProp_GProps
from OCCT.gp import gp_Pnt, gp_Vec

from OCCT.TopAbs import (
    TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_WIRE,
    TopAbs_SHELL, TopAbs_SOLID, TopAbs_COMPOUND,
    TopAbs_COMPSOLID
)
from OCCT.TopExp import TopExp, TopExp_Explorer
from OCCT.TopoDS import (
    TopoDS, TopoDS_Wire, TopoDS_Vertex, TopoDS_Edge,
    TopoDS_Face, TopoDS_Shell, TopoDS_Solid,
    TopoDS_Compound, TopoDS_CompSolid, TopoDS_Shape, TopoDS_Iterator
)
from OCCT.TopTools import (
    TopTools_ListOfShape,
    TopTools_ListIteratorOfListOfShape,
    TopTools_IndexedDataMapOfShapeListOfShape
)

from ..shape import BBox, coerce_point, coerce_direction


DISCRETIZE_METHODS = {
    'deflection': GCPnts_UniformDeflection,
    'quasi-deflection': GCPnts_QuasiUniformDeflection,
    'quasi-abscissa': GCPnts_QuasiUniformAbscissa,
    'abscissa': GCPnts_UniformAbscissa,
}


class WireExplorer(Atom):
    """ Wire traversal ported from the pythonocc examples by @jf--

    """
    wire = Instance(TopoDS_Wire)
    wire_explorer = Typed(BRepTools_WireExplorer)

    def _loop_topo(self, edges=True):
        wexp = self.wire_explorer = BRepTools_WireExplorer(self.wire)

        items = set()  # list that stores hashes to avoid redundancy
        occ_seq = TopTools_ListOfShape()

        get_current = wexp.Current if edges else wexp.CurrentVertex

        while wexp.More():
            current_item = get_current()
            if current_item not in items:
                items.add(current_item)
                occ_seq.Append(current_item)
            wexp.Next()

        # Convert occ_seq to python list
        seq = []
        topology_type = TopoDS.Edge_ if edges else TopoDS.Vertex_
        occ_iterator = TopTools_ListIteratorOfListOfShape(occ_seq)
        while occ_iterator.More():
            topo_to_add = topology_type(occ_iterator.Value())
            seq.append(topo_to_add)
            occ_iterator.Next()
        return seq

    def ordered_edges(self):
        return self._loop_topo(edges=True)

    def ordered_vertices(self):
        return self._loop_topo(edges=False)


class Topology(Atom):
    """ Topology traversal ported from the pythonocc examples by @jf---

    Implements topology traversal from any TopoDS_Shape this class lets you
    find how various topological entities are connected from one to another
    find the faces connected to an edge, find the vertices this edge is
    made from, get all faces connected to a vertex, and find out how many
    topological elements are connected from a source


    Note
    ----
    when traversing TopoDS_Wire entities, its advised to use the
    specialized ``WireExplorer`` class, which will return the vertices /
    edges in the expected order

    """

    #: Maps topology types and functions that can create this topology
    topo_factory = {
        TopAbs_VERTEX: TopoDS.Vertex_,
        TopAbs_EDGE: TopoDS.Edge_,
        TopAbs_FACE: TopoDS.Face_,
        TopAbs_WIRE: TopoDS.Wire_,
        TopAbs_SHELL: TopoDS.Shell_,
        TopAbs_SOLID: TopoDS.Solid_,
        TopAbs_COMPOUND: TopoDS.Compound_,
        TopAbs_COMPSOLID: TopoDS.CompSolid_
    }

    topo_types = {
        TopAbs_VERTEX: TopoDS_Vertex,
        TopAbs_EDGE: TopoDS_Edge,
        TopAbs_FACE: TopoDS_Face,
        TopAbs_WIRE: TopoDS_Wire,
        TopAbs_SHELL: TopoDS_Shell,
        TopAbs_SOLID: TopoDS_Solid,
        TopAbs_COMPOUND: TopoDS_Compound,
        TopAbs_COMPSOLID: TopoDS_CompSolid
    }

    curve_factory = {
        GeomAbs_Line: lambda c: GC_MakeSegment(
                c.Line(), c.FirstParameter(), c.LastParameter()).Value(),
        GeomAbs_Circle: lambda c: Geom_Circle(c.Circle()),
        GeomAbs_Ellipse: lambda c: Geom_Ellipse(c.Ellipse()),
        GeomAbs_Hyperbola: lambda c: Geom_Hyperbola(c.Hyperbola()),
        GeomAbs_Parabola: lambda c: Geom_Parabola(c.Parabola()),
        GeomAbs_BezierCurve: BRepAdaptor_Curve.Bezier,
        GeomAbs_BSplineCurve: BRepAdaptor_Curve.BSpline,
        GeomAbs_OffsetCurve: BRepAdaptor_Curve.OffsetCurve,
        GeomAbs_OtherCurve: BRepAdaptor_CompCurve,
    }

    surface_factory = {
        GeomAbs_Cylinder: lambda s: s.Cylinder(),
    }

    #: The shape which topology will be traversed
    shape = Instance(TopoDS_Shape)

    #: Filter out TopoDS_* entities of similar TShape but different orientation
    #: for instance, a cube has 24 edges, 4 edges for each of 6 faces
    #: that results in 48 vertices, while there are only 8 vertices that have
    #: a unique geometric coordinate
    #: in certain cases ( computing a graph from the topology ) its preferable
    #: to return topological entities that share similar geometry, though
    #: differ in orientation by setting the ``ignore_orientation`` variable
    #: to True, in case of a cube, just 12 edges and only 8 vertices will be
    #: returned
    #: for further reference see TopoDS_Shape IsEqual / IsSame methods
    ignore_orientation = Bool()

    def _loop_topo(self, topology_type, topological_entity=None,
                   topology_type_to_avoid=None):
        """ this could be a faces generator for a python TopoShape class
        that way you can just do:
        for face in srf.faces:
            processFace(face)
        """
        allowed_types = self.topo_types.keys()
        if topology_type not in allowed_types:
            raise TypeError('%s not one of %s' % (
                topology_type, allowed_types))

        shape = self.shape
        if shape is None:
            return []

        topo_exp = TopExp_Explorer()
        # use self.myShape if nothing is specified
        if topological_entity is None and topology_type_to_avoid is None:
            topo_exp.Init(shape, topology_type)
        elif topological_entity is None and topology_type_to_avoid is not None:
            topo_exp.Init(shape, topology_type, topology_type_to_avoid)
        elif topology_type_to_avoid is None:
            topo_exp.Init(topological_entity, topology_type)
        elif topology_type_to_avoid:
            topo_exp.Init(
                topological_entity, topology_type, topology_type_to_avoid)

        items = set()  # list that stores hashes to avoid redundancy
        occ_seq = TopTools_ListOfShape()
        while topo_exp.More():
            current_item = topo_exp.Current()
            if current_item not in items:
                items.add(current_item)
                occ_seq.Append(current_item)
            topo_exp.Next()

        # Convert occ_seq to python list
        seq = []
        factory = self.topo_factory[topology_type]
        occ_iterator = TopTools_ListIteratorOfListOfShape(occ_seq)
        while occ_iterator.More():
            topo_to_add = factory(occ_iterator.Value())
            seq.append(topo_to_add)
            occ_iterator.Next()

        if not self.ignore_orientation:
            return seq

        # else filter out those entities that share the same TShape
        # but do *not* share the same orientation
        filter_orientation_seq = []
        for i in seq:
            present = False
            for j in filter_orientation_seq:
                if i.IsSame(j):
                    present = True
                    break
            if present is False:
                filter_orientation_seq.append(i)
        return filter_orientation_seq

    # -------------------------------------------------------------------------
    # Shape Topology
    # -------------------------------------------------------------------------
    faces = List()

    def _default_faces(self):
        return self._loop_topo(TopAbs_FACE)

    vertices = List()

    def _default_vertices(self):
        return self._loop_topo(TopAbs_VERTEX)

    #: Get a list of points from verticies
    points = List()

    def _default_points(self):
        return [coerce_point(v) for v in self.vertices]

    edges = List()

    def _default_edges(self):
        return self._loop_topo(TopAbs_EDGE)

    wires = List()

    def _default_wires(self):
        return self._loop_topo(TopAbs_WIRE)

    shells = List()

    def _default_shells(self):
        return self._loop_topo(TopAbs_SHELL)

    solids = List()

    def _default_solids(self):
        return self._loop_topo(TopAbs_SOLID)

    comp_solids = List()

    def _default_comp_solids(self):
        return self._loop_topo(TopAbs_COMPSOLID)

    compounds = List()

    def _default_compounds(self):
        return self._loop_topo(TopAbs_COMPOUND)

    def ordered_vertices_from_wire(self, wire):
        """ Get verticies from a wire.

        Parameters
        ----------
        wire: TopoDS_Wire
        """
        return WireExplorer(wire=wire).ordered_vertices()

    def ordered_edges_from_wire(self, wire):
        """ Get edges from a wire.

        Parameters
        ----------
        wire: TopoDS_Wire
        """
        return WireExplorer(wire=wire).ordered_edges()

    def _map_shapes_and_ancestors(self, topo_type_a, topo_type_b, topo_entity):
        '''
        using the same method
        @param topoTypeA:
        @param topoTypeB:
        @param topological_entity:
        '''
        topo_set = set()
        items = []
        topo_map = TopTools_IndexedDataMapOfShapeListOfShape()
        TopExp.MapShapesAndAncestors_(
            self.shape, topo_type_a, topo_type_b, topo_map)
        topo_results = topo_map.FindFromKey(topo_entity)
        if topo_results.IsEmpty():
            return []

        topology_iterator = TopTools_ListIteratorOfListOfShape(topo_results)
        factory = self.topo_factory[topo_type_b]

        while topology_iterator.More():
            topo_entity = factory(topology_iterator.Value())

            # return the entity if not in set
            # to assure we're not returning entities several times
            if topo_entity not in topo_set:
                if self.ignore_orientation:
                    unique = True
                    for i in topo_set:
                        if i.IsSame(topo_entity):
                            unique = False
                            break
                    if unique:
                        items.append(topo_entity)
                else:
                    items.append(topo_entity)

            topo_set.add(topo_entity)
            topology_iterator.Next()
        return items

    # ----------------------------------------------------------------------
    # EDGE <-> FACE
    # ----------------------------------------------------------------------
    def faces_from_edge(self, edge):
        """

        :param edge:
        :return:
        """
        return self._map_shapes_and_ancestors(TopAbs_EDGE, TopAbs_FACE, edge)

    def edges_from_face(self, face):
        """

        :param face:
        :return:
        """
        return self._loop_topo(TopAbs_EDGE, face)

    # ----------------------------------------------------------------------
    # VERTEX <-> EDGE
    # ----------------------------------------------------------------------
    def vertices_from_edge(self, edg):
        return self._loop_topo(TopAbs_VERTEX, edg)

    def edges_from_vertex(self, vertex):
        return self._map_shapes_and_ancestors(
            TopAbs_VERTEX, TopAbs_EDGE, vertex)

    # ----------------------------------------------------------------------
    # WIRE <-> EDGE
    # ----------------------------------------------------------------------
    def edges_from_wire(self, wire):
        return self._loop_topo(TopAbs_EDGE, wire)

    def wires_from_edge(self, edg):
        return self._map_shapes_and_ancestors(TopAbs_EDGE, TopAbs_WIRE, edg)

    def wires_from_vertex(self, edg):
        return self._map_shapes_and_ancestors(TopAbs_VERTEX, TopAbs_WIRE, edg)

    # ----------------------------------------------------------------------
    # WIRE <-> FACE
    # ----------------------------------------------------------------------
    def wires_from_face(self, face):
        return self._loop_topo(TopAbs_WIRE, face)

    def faces_from_wire(self, wire):
        return self._map_shapes_and_ancestors(TopAbs_WIRE, TopAbs_FACE, wire)

    # ----------------------------------------------------------------------
    # VERTEX <-> FACE
    # ----------------------------------------------------------------------
    def faces_from_vertex(self, vertex):
        return self._map_shapes_and_ancestors(
            TopAbs_VERTEX, TopAbs_FACE, vertex)

    def vertices_from_face(self, face):
        return self._loop_topo(TopAbs_VERTEX, face)

    # ----------------------------------------------------------------------
    # FACE <-> SOLID
    # ----------------------------------------------------------------------
    def solids_from_face(self, face):
        return self._map_shapes_and_ancestors(TopAbs_FACE, TopAbs_SOLID, face)

    def faces_from_solids(self, solid):
        return self._loop_topo(TopAbs_FACE, solid)

    # -------------------------------------------------------------------------
    # Surface Types
    # -------------------------------------------------------------------------
    def extract_surfaces(self, surface_type):
        """ Returns a list of dicts containing the face and surface

        """
        surfaces = []
        attr = str(surface_type).split("_")[-1]
        for f in self.faces:
            surface = self.cast_surface(f, surface_type)
            if surface is not None:
                surfaces.append({
                    'face': f, 'surface': getattr(surface, attr)()})
        return surfaces

    plane_surfaces = List()

    def _default_plane_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Plane)

    cone_surfaces = List()

    def _default_cone_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Cone)

    sphere_surfaces = List()

    def _default_sphere_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Sphere)

    torus_surfaces = List()

    def _default_torus_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Torus)

    cone_surfaces = List()

    def _default_cone_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Cone)

    cylinder_surfaces = List()

    def _default_cylinder_surface(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_Cylinder)

    bezier_surfaces = List()

    def _default_bezier_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_BezierSurface)

    bspline_surfaces = List()

    def _default_bspline_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_BSplineSurface)

    offset_surfaces = List()

    def _default_offset_surfaces(self):
        return self.extract_surfaces(GeomAbs.GeomAbs_OffsetSurface)

    # -------------------------------------------------------------------------
    # Curve Types
    # -------------------------------------------------------------------------
    def extract_curves(self, curve_type):
        """ Returns a list of tuples containing the edge and curve

        """
        curves = []
        for e in self.edges:
            curve = self.cast_curve(e, curve_type)
            if curve is not None:
                curves.append({'edge': e, 'curve': curve})
        return curves

    line_curves = List()

    def _default_line_curves(self):
        return self.extract_curves(GeomAbs_Line)

    circle_curves = List()

    def _default_circle_curves(self):
        return self.extract_curves(GeomAbs_Circle)

    ellipse_curves = List()

    def _default_ellipse_curves(self):
        return self.extract_curves(GeomAbs_Ellipse)

    hyperbola_curves = List()

    def _default_hyperbola_curves(self):
        return self.extract_curves(GeomAbs_Hyperbola)

    parabola_cuves = List()

    def _default_parabola_cuves(self):
        return self.extract_curves(GeomAbs_Parabola)

    bezier_curves = List()

    def _default_bezier_curves(self):
        return self.extract_curves(GeomAbs_BezierCurve)

    bspline_curves = List()

    def _default_bspline_curves(self):
        return self.extract_curves(GeomAbs_BSplineCurve)

    offset_curves = List()

    def _default_offset_curves(self):
        return self.extract_curves(GeomAbs_OffsetCurve)

    curves = List()

    def _default_curves(self):
        return self.extract_curves(None)

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------
    @classmethod
    def cast_shape(cls, topods_shape):
        """ Convert a TopoDS_Shape into it's actual type, ex an TopoDS_Edge

        Parameters
        -----------
        topods_shape: TopoDS_Shape
            The shape to cas

        Returns
        -------
        shape: TopoDS_Shape
            The actual shape.

        """
        return cls.topo_factory[topods_shape.ShapeType()](topods_shape)

    @classmethod
    def cast_curve(cls, shape, expected_type=None):
        """ Attempt to cast the shape (an edge or wire) to a curve

        Parameters
        ----------
        shape: TopoDS_Edge
            The shape to cast
        expected_type: GeomAbs_CurveType
            The type to restrict

        Returns
        -------
        curve: Curve or None
            The curve or None if it could not be created or if it was not
            of the expected type (if given).
        """
        edge = TopoDS.Edge_(shape)
        curve = BRepAdaptor_Curve(edge)
        t = curve.GetType()
        return cls.curve_factory[t](curve)

    @classmethod
    def cast_surface(cls, shape, expected_type=None):
        """ Attempt to cast the shape (a face) to a surface

        Parameters
        ----------
        shape: TopoDS_Face
            The shape to cast
        expected_type: GeomAbs_SurfaceType
            The type to restrict

        Returns
        -------
        surface: BRepAdaptor_Surface or None
            The surface or None if it could not be created or did not
            match the expected type (if given).
        """
        if isinstance(shape, TopoDS_Face):
            face = shape
        else:
            face = TopoDS.Face_(shape)
        surface = BRepAdaptor_Surface(face, True)
        if expected_type is not None and surface.GetType() != expected_type:
            return None
        return surface

    @classmethod
    def is_circle(cls, shape):
        """ Check if an edge or wire is a part of a circle.
        This can be used to see if an edge can be used for radius dimensions.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of circle
        """
        edge = TopoDS.Edge_(shape)
        curve = BRepAdaptor_Curve(edge)
        return curve.GetType() == GeomAbs.GeomAbs_Circle

    @classmethod
    def is_ellipse(cls, shape):
        """ Check if an edge or wire is a part of an ellipse.
        This can be used to see if an edge can be used for radius dimensions.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of an ellipse
        """
        edge = TopoDS.Edge_(shape)
        curve = BRepAdaptor_Curve(edge)
        return curve.GetType() == GeomAbs.GeomAbs_Ellipse

    @classmethod
    def is_line(cls, shape):
        """ Check if an edge or wire is a line.
        This can be used to see if an edge can be used for length dimensions.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of a line
        """
        edge = TopoDS.Edge_(shape)
        curve = BRepAdaptor_Curve(edge)
        return curve.GetType() == GeomAbs.GeomAbs_Line

    @classmethod
    def is_plane(cls, shape):
        """ Check if a surface is a plane.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of a line
        """
        surface = cls.cast_surface(shape)
        if surface is None:
            return False
        return surface.GetType() == GeomAbs.GeomAbs_Plane

    @classmethod
    def is_cylinder(cls, shape):
        """ Check if a surface is a cylinder.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of a line
        """
        surface = cls.cast_surface(shape)
        if surface is None:
            return False
        return surface.GetType() == GeomAbs.GeomAbs_Cylinder

    @classmethod
    def is_shape_in_list(cls, shape, shapes):
        """ Check if an shape is in a list of shapes using the IsSame method.

        Parameters
        ----------
        shape: TopoDS_Shape
            The shape to check
        shapes: Iterable[TopoDS_Shape]
            An interable of shapes to check against

        Returns
        -------
        bool: Bool
            Whether the shape is in the list
        """
        if not isinstance(shape, TopoDS_Shape):
            raise TypeError("Expected a TopoDS_Shape instance")
        return any(shape.IsSame(s) for s in shapes)

    @classmethod
    def get_value_at(cls, curve, t, derivative=0):
        """ Get the value of the curve at parameter t with it's derivatives.

        Parameters
        ----------
        curve: BRepAdaptor_Curve
            The curve to get the value from
        t: Float
            The parameter value from 0 to 1
        derivative: Int
            The derivative from 0 to 4

        Returns
        -------
        results: Point or Tuple
            If the derivative is 0 only the position at t is returned,
            otherwise a tuple of the position and all deriviatives.
        """
        p = gp_Pnt()
        if derivative == 0:
            curve.D0(t, p)
            return coerce_point(p)
        v1 = gp_Vec()
        if derivative == 1:
            curve.D1(t, p, v1)
            return (coerce_point(p), coerce_direction(v1))
        v2 = gp_Vec()
        if derivative == 2:
            curve.D1(t, p, v1, v2)
            return (coerce_point(p), coerce_direction(v1),
                    coerce_direction(v2))
        v3 = gp_Vec()
        if derivative == 3:
            curve.D3(t, p, v1, v2, v3)
            return (coerce_point(p), coerce_direction(v1),
                    coerce_direction(v2), coerce_direction(v3))
        raise ValueError("Invalid derivative")

    @classmethod
    def discretize(cls, wire, deflection, method='quasi-deflection'):
        """ Convert a wire to points.

        Parameters
        ----------
        deflection: Float or Int
            Maximum deflection allowed if method is 'deflection' or
            'quasi-'defelction' else this is the number of points
        n: Int
            Number of points to use
        methode: Str
            A value of either 'deflection' or 'abissca'
        Returns
        -------
        points: List[Point]
            A list of points that make up the curve

        """
        c = BRepAdaptor_CompCurve(wire)
        start = c.FirstParameter()
        end = c.LastParameter()
        fn = DISCRETIZE_METHODS[method.lower().replace('uniform', '')]
        a = fn(c, deflection, start, end)
        if method.endswith('abscissa'):
            param = lambda i: c.Value(a.Parameter(i))
        else:
            param = lambda i: a.Value(i)
        return [coerce_point(param(i)) for i in range(1, a.NbPoints()+1)]

    @classmethod
    def bbox(cls, shapes, optimal=False, tolerance=0):
        """ Compute the bounding box of the shape or list of shapes

        Parameters
        ----------
        shapes: Shape, TopoDS_Shape or list of them
            The shapes to compute the bounding box for

        Returns
        -------
        bbox: BBox
            The boudning g

        """
        from .occ_shape import coerce_shape
        if not shapes:
            return BBox()
        bbox = Bnd_Box()
        bbox.SetGap(tolerance)
        if not isinstance(shapes, (list, tuple, set)):
            shapes = [shapes]
        add = BRepBndLib.AddOptimal_ if optimal else BRepBndLib.Add_
        for s in shapes:
            add(coerce_shape(s), bbox)
        pmin, pmax = bbox.CornerMin(), bbox.CornerMax()
        return BBox(*(pmin.X(), pmin.Y(), pmin.Z(),
                      pmax.X(), pmax.Y(), pmax.Z()))

    # -------------------------------------------------------------------------
    # Edge/Wire Properties
    # -------------------------------------------------------------------------
    @property
    def length(self):
        props = GProp_GProps()
        BRepGProp.LinearProperties_(self.shape, props, True)
        return props.Mass()  # Don't ask

    @property
    def start_point(self):
        """ Get the first / start point of a TopoDS_Wire or TopoDS_Edge

        """
        curve = BRepAdaptor_CompCurve(self.shape)
        return self.get_value_at(curve, curve.FirstParameter())

    @property
    def end_point(self):
        """ Get the end / last point of a TopoDS_Wire or TopoDS_Edge

        """
        curve = BRepAdaptor_CompCurve(self.shape)
        return self.get_value_at(curve, curve.LastParameter())


    # -------------------------------------------------------------------------
    # Shape Properties
    # -------------------------------------------------------------------------
    mass = length

    # -------------------------------------------------------------------------
    # Intersection
    # -------------------------------------------------------------------------
    def intersection(self, shape):
        """ Returns the resulting intersection of this and the given shape
        or None.

        """
        op = BOPAlgo_Section()
        op.AddArgument(self.shape)
        op.AddArgument(shape)
        op.Perform()
        if op.HasErrors():
            return
        r = op.Shape()
        if r.IsNull():
            return
        n = r.NbChildren()
        if n == 0:
            return
        it = TopoDS_Iterator(r)
        results = []
        while it.More():
            results.append(Topology.cast_shape(it.Value()))
            it.Next()
        return results
