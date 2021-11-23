"""
Copyright (c) 2016-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 30, 2016

@author: jrm
"""
from atom.api import Atom, Instance, Typed, Bool, List
from typing import Any, Iterable, Optional, TypeVar, Union
from typing import Dict as DictType
from typing import List as ListType
from typing import Set as SetType
from typing import Tuple as TupleType
from OCCT import GeomAbs
from OCCT.BOPAlgo import BOPAlgo_Section
from OCCT.Bnd import Bnd_Box
from OCCT.BRepBuilderAPI import (
    BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeVertex,
    BRepBuilderAPI_MakeFace
)
from OCCT.BRepAdaptor import (
    BRepAdaptor_Curve, BRepAdaptor_CompCurve, BRepAdaptor_Surface
)
from OCCT.BRepBndLib import BRepBndLib
from OCCT.BRepTools import BRepTools, BRepTools_WireExplorer
from OCCT.BRepExtrema import BRepExtrema_DistShapeShape
from OCCT.BRepGProp import BRepGProp
from OCCT.GC import GC_MakeSegment
from OCCT.GCPnts import (
    GCPnts_UniformDeflection, GCPnts_QuasiUniformDeflection,
    GCPnts_UniformAbscissa, GCPnts_QuasiUniformAbscissa
)
from OCCT.Geom import (
    Geom_Ellipse, Geom_Circle, Geom_Parabola, Geom_Hyperbola, Geom_Line,
    Geom_TrimmedCurve, Geom_Curve, Geom_Surface
)
from OCCT.GeomAbs import (
    GeomAbs_Line, GeomAbs_Circle, GeomAbs_Ellipse, GeomAbs_Hyperbola,
    GeomAbs_Parabola, GeomAbs_BezierCurve, GeomAbs_BSplineCurve,
    GeomAbs_OffsetCurve, GeomAbs_OtherCurve,
    GeomAbs_SurfaceType, GeomAbs_CurveType,
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Torus,
    GeomAbs_Sphere
)
from OCCT.GProp import GProp_GProps
from OCCT.gp import gp_Pnt, gp_Vec
from OCCT.Extrema import Extrema_ExtFlag_MAX, Extrema_ExtFlag_MIN
from OCCT.TopAbs import (
    TopAbs_VERTEX, TopAbs_EDGE, TopAbs_FACE, TopAbs_WIRE,
    TopAbs_SHELL, TopAbs_SOLID, TopAbs_COMPOUND,
    TopAbs_COMPSOLID, TopAbs_REVERSED, TopAbs_ShapeEnum
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
    TopTools_IndexedDataMapOfShapeListOfShape,
    TopTools_HSequenceOfShape
)

from OCCT.ShapeAnalysis import ShapeAnalysis_FreeBounds

from ..shape import Direction, Point, BBox, coerce_point, coerce_direction

T = TypeVar('T')

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

    def _loop_topo(self, edges: bool = True) -> list:
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

    def ordered_edges(self) -> ListType[TopoDS_Edge]:
        return self._loop_topo(edges=True)

    def ordered_vertices(self) -> ListType[TopoDS_Vertex]:
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
        GeomAbs_Cone: lambda s: s.Cone(),
        GeomAbs_Plane: lambda s: s.Plane(),
        GeomAbs_Sphere: lambda s: s.Sphere(),
        GeomAbs_Torus: lambda s: s.Torus(),
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

    #: Get a list of points from vertices
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

    def ordered_vertices_from_wire(
        self,
        wire: TopoDS_Wire
    ) -> ListType[TopoDS_Vertex]:
        """ Get vertices from a wire.

        Parameters
        ----------
        wire: TopoDS_Wire
        """
        return WireExplorer(wire=wire).ordered_vertices()

    def ordered_edges_from_wire(
        self,
        wire: TopoDS_Wire
    ) -> ListType[TopoDS_Edge]:
        """ Get edges from a wire.

        Parameters
        ----------
        wire: TopoDS_Wire
        """
        return WireExplorer(wire=wire).ordered_edges()

    def _map_shapes_and_ancestors(
        self,
        topo_type_a: TopAbs_ShapeEnum,
        topo_type_b: TopAbs_ShapeEnum,
        topo_entity: TopoDS_Shape
    ) -> ListType[TopoDS_Shape]:
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
    def faces_from_edge(self, edge: TopoDS_Edge) -> ListType[TopoDS_Face]:
        return self._map_shapes_and_ancestors(TopAbs_EDGE, TopAbs_FACE, edge)

    def edges_from_face(self, face: TopoDS_Face) -> ListType[TopoDS_Edge]:
        return self._loop_topo(TopAbs_EDGE, face)

    def find_common_edges(self, shape: TopoDS_Shape) -> SetType[TopoDS_Edge]:
        """ Find edges common to this shape and the given shape

        Parameters
        ----------
        shape: TopoDS_Shape
            The other shape to find common edges with

        Returns
        -------
        edges: List[TopoDS_Edge]
            The edges that are considered the same in both shapes.

        """
        common = set()
        other_edges = Topology(shape=shape).edges
        for edge in self.edges:
            for other_edge in other_edges:
                if edge.IsSame(other_edge):
                    common.add(edge)
        return common

    @classmethod
    def find_unique_edges(
        cls,
        shapes: Iterable[TopoDS_Shape]
    ) -> SetType[TopoDS_Edge]:
        """ Find edges unique to only one shape in the set of shapes.

        Parameters
        ----------
        shapes: Iterable[TopoDS_Shape]
            The shapes to find the set of unique edges from.

        """
        unique_edges = set()
        edge_map = {s: Topology(shape=s).edges for s in shapes}
        remaining = [s for s in shapes]
        while remaining:
            shape = remaining.pop()
            for edge in edge_map.pop(shape):
                unique = True
                for other_shape in remaining:
                    other_edges = edge_map[other_shape]
                    for other_edge in other_edges[:]:
                        if edge.IsSame(other_edge):
                            other_edges.remove(other_edge)
                            unique = False
                if unique:
                    unique_edges.add(edge)
        return unique_edges

    @classmethod
    def join_edges(
        cls,
        edges: Iterable[TopoDS_Edge],
        tolerance=1e-6
    ) -> ListType[TopoDS_Wire]:
        """ Join a set of edges into a set of wires.

        Parameters
        ----------
        edges: Iterable[TopoDS_Edge]
            The edges to join

        Returns
        -------
        wires: List[TopoDS_Wire]
            The wires connected.

        """
        seq = TopTools_HSequenceOfShape()
        for e in edges:
            seq.Append(e)
        r = ShapeAnalysis_FreeBounds.ConnectEdgesToWires_(
            seq, tolerance, False)
        return [Topology.cast_shape(r.Value(i)) for i in range(1, r.Size()+1)]

    # ----------------------------------------------------------------------
    # VERTEX <-> EDGE
    # ----------------------------------------------------------------------
    def vertices_from_edge(self, edge: TopoDS_Edge) -> ListType[TopoDS_Vertex]:
        return self._loop_topo(TopAbs_VERTEX, edge)

    def edges_from_vertex(
        self,
        vertex: TopoDS_Vertex
    ) -> ListType[TopoDS_Edge]:
        return self._map_shapes_and_ancestors(
            TopAbs_VERTEX, TopAbs_EDGE, vertex)

    def find_common_vertices(
        self,
        shape: TopoDS_Shape
    ) -> SetType[TopoDS_Vertex]:
        """ Find edges common to this shape and the given shape

        Parameters
        ----------
        shape: TopoDS_Shape
            The other shape to find common edges with

        Returns
        -------
        edges: List[TopoDS_Edge]
            The edges that are considered the same in both shapes.

        """
        common = set()
        other_vertices = Topology(shape=shape).vertices
        for vertex in self.vertices:
            for other_vertex in other_vertices:
                if vertex.IsSame(other_vertices):
                    common.add(vertex)
        return common

    # ----------------------------------------------------------------------
    # WIRE <-> EDGE
    # ----------------------------------------------------------------------
    def edges_from_wire(self, wire: TopoDS_Wire) -> ListType[TopoDS_Edge]:
        return self._loop_topo(TopAbs_EDGE, wire)

    def wires_from_edge(self, edge: TopoDS_Edge) -> ListType[TopoDS_Wire]:
        return self._map_shapes_and_ancestors(TopAbs_EDGE, TopAbs_WIRE, edge)

    def wires_from_vertex(
        self,
        vertex: TopoDS_Vertex
    ) -> ListType[TopoDS_Vertex]:
        return self._map_shapes_and_ancestors(
            TopAbs_VERTEX, TopAbs_WIRE, vertex)

    # ----------------------------------------------------------------------
    # WIRE <-> FACE
    # ----------------------------------------------------------------------
    def wires_from_face(self, face: TopoDS_Face) -> ListType[TopoDS_Wire]:
        return self._loop_topo(TopAbs_WIRE, face)

    def faces_from_wire(self, wire: TopoDS_Wire) -> ListType[TopoDS_Face]:
        return self._map_shapes_and_ancestors(TopAbs_WIRE, TopAbs_FACE, wire)

    # ----------------------------------------------------------------------
    # VERTEX <-> FACE
    # ----------------------------------------------------------------------
    def faces_from_vertex(
        self,
        vertex: TopoDS_Vertex
    ) -> ListType[TopoDS_Face]:
        return self._map_shapes_and_ancestors(
            TopAbs_VERTEX, TopAbs_FACE, vertex)

    def vertices_from_face(self, face: TopoDS_Face) -> ListType[TopoDS_Vertex]:
        return self._loop_topo(TopAbs_VERTEX, face)

    # ----------------------------------------------------------------------
    # FACE <-> SOLID
    # ----------------------------------------------------------------------
    def solids_from_face(self, face: TopoDS_Face) -> ListType[TopoDS_Solid]:
        return self._map_shapes_and_ancestors(TopAbs_FACE, TopAbs_SOLID, face)

    def faces_from_solids(self, solid: TopoDS_Solid) -> ListType[TopoDS_Face]:
        return self._loop_topo(TopAbs_FACE, solid)

    # -------------------------------------------------------------------------
    # Surface Types
    # -------------------------------------------------------------------------
    def extract_surfaces(
        self,
        surface_type: GeomAbs_SurfaceType
    ) -> ListType[DictType[str, Any]]:
        """ Returns a list of dicts containing the face and surface

        """
        surfaces = []
        attr = str(surface_type).split("_")[-1]
        for f in self.faces:
            surface = self.cast_surface(f, surface_type)
            if surface is not None:
                surfaces.append({'face': f, 'surface': surface})
        return surfaces

    plane_surfaces = List()

    def _default_plane_surfaces(self):
        return self.extract_surfaces(GeomAbs_Plane)

    sphere_surfaces = List()

    def _default_sphere_surfaces(self):
        return self.extract_surfaces(GeomAbs_Sphere)

    torus_surfaces = List()

    def _default_torus_surfaces(self):
        return self.extract_surfaces(GeomAbs_Torus)

    cone_surfaces = List()

    def _default_cone_surfaces(self):
        return self.extract_surfaces(GeomAbs_Cone)

    cylinder_surfaces = List()

    def _default_cylinder_surface(self):
        return self.extract_surfaces(GeomAbs_Cylinder)

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
    # Shape introspection
    # -------------------------------------------------------------------------
    @classmethod
    def cast_shape(cls, topods_shape: TopoDS_Shape) -> TopoDS_Shape:
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
    def cast_curve(
        cls,
        shape: TopoDS_Edge,
        expected_type: Optional[GeomAbs_CurveType] = None,
        convert: bool = True,
    ) -> Optional[Union[Geom_Curve, BRepAdaptor_Curve]]:
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
        if expected_type is not None and t != expected_type:
            return None
        if convert:
            factory = cls.curve_factory.get(t)
            if factory:
                return factory(curve)
        return curve

    @classmethod
    def cast_surface(
        cls,
        shape: TopoDS_Face,
        expected_type: Optional[GeomAbs_SurfaceType] = None,
        convert: bool = True,
    ) -> Optional[Union[Geom_Surface, BRepAdaptor_Surface]]:
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
        face = TopoDS.Face_(shape)
        surface = BRepAdaptor_Surface(face, True)
        t = surface.GetType()
        if expected_type is not None and t != expected_type:
            return None
        if convert:
            factory = cls.surface_factory.get(t)
            if factory:
                return factory(surface)
        return surface

    @classmethod
    def is_vertex(cls, shape) -> bool:
        """ Check if the given shape is a vertex.

        Returns
        -------
        result: Bool
            Whether the shape is an vertex.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_VERTEX
        return False

    @classmethod
    def is_edge(cls, shape) -> bool:
        """ Check if the given shape is an edge.

        Returns
        -------
        result: Bool
            Whether the shape is an edge.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_EDGE
        return False

    @classmethod
    def is_wire(cls, shape) -> bool:
        """ Check if the given shape is a face.

        Returns
        -------
        result: Bool
            Whether the shape is a face.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_WIRE
        return False

    @classmethod
    def is_face(cls, shape) -> bool:
        """ Check if the given shape is a face.

        Returns
        -------
        result: Bool
            Whether the shape is a face.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_FACE
        return False

    @classmethod
    def is_shell(cls, shape) -> bool:
        """ Check if the given shape is a shell.

        Returns
        -------
        result: Bool
            Whether the shape is a shell.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_SHELL
        return False

    @classmethod
    def is_solid(cls, shape) -> bool:
        """ Check if the given shape is a solid.

        Returns
        -------
        result: Bool
            Whether the shape is a solid.

        """
        if isinstance(shape, TopoDS_Shape):
            return shape.ShapeType() == TopAbs_SOLID
        return False

    @classmethod
    def is_circle(cls, shape) -> bool:
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
    def is_ellipse(cls, shape) -> bool:
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
    def is_line(cls, shape) -> bool:
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
    def is_plane(cls, shape) -> bool:
        """ Check if a surface is a plane.

        Returns
        -------
        bool: Bool
            Whether the shape is a part of a line
        """
        return cls.cast_surface(
            shape,
            expected_type=GeomAbs_Plane,
            convert=False) is not None

    @classmethod
    def is_cylinder(cls, shape) -> bool:
        """ Check if a surface is a cylinder.

        Returns
        -------
        result: Bool
            Whether the shape is a cylinder
        """
        return cls.cast_surface(
            shape,
            expected_type=GeomAbs_Cylinder,
            convert=False) is not None

    @classmethod
    def is_cone(cls, shape) -> bool:
        """ Check if a surface is a cone.

        Returns
        -------
        bool: Bool
            Whether the shape is a cone
        """
        return cls.cast_surface(
            shape,
            expected_type=GeomAbs_Cone,
            convert=False) is not None

    @classmethod
    def is_reversed(cls, shape) -> bool:
        """ Check if the shape's orentation is reversed.

        Returns
        -------
        result: bool
            Whether the shape's orentation is reversed.

        """
        return shape.Orientation() == TopAbs_REVERSED

    @classmethod
    def is_clockwise(cls, shape: TopoDS_Shape) -> bool:
        """ Check if the face or wire's orientation is clockwise relative
        to the postive Z axis.

        Returns
        -------
        result: bool
            Whether the shape's orentation is reversed.

        """
        if isinstance(shape, TopoDS_Wire):
            face = BRepBuilderAPI_MakeFace(shape).Face()
        else:
            face = shape
        return Topology(shape=face).area > 0

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
    def are_faces_connected(
        cls,
        face: TopoDS_Face,
        other_face: TopoDS_Face
    ) -> bool:
        """ Check if two faces are connected by one of their edges.

        Parameters
        ----------
        face: TopoDS_Face
            Face to check connection with
        other_face: TopoDS_Face
            Face to check connection to

        Returns
        -------
        result: bool
            True if any of the edges are the same

        """
        # TODO: Is there a OCCT function to do this?
        other_edges = cls(shape=other_face).edges
        for e in cls(shape=face).edges:
            if cls.is_shape_in_list(e, other_edges):
                return True
        return False

    # -------------------------------------------------------------------------
    # Parametrization
    # -------------------------------------------------------------------------
    @classmethod
    def get_value_at(cls, curve, t, derivative=0):
        return cls.curve_value_at(curve, t, derivative)

    @classmethod
    def curve_value_at(cls, curve, t, derivative=0):
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
    def surface_value_at(cls, surface, u, v, derivative=0):
        """ Get the value of the surface at parameter t with it's derivatives.

        Parameters
        ----------
        surface: BRepAdaptor_Surface
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
            surface.D0(u, v, p)
            return coerce_point(p)
        v1 = gp_Vec()
        if derivative == 1:
            surface.D1(u, v, p, v1)
            return (coerce_point(p), coerce_direction(v1))
        v2 = gp_Vec()
        if derivative == 2:
            surface.D1(u, v, p, v1, v2)
            return (coerce_point(p), coerce_direction(v1),
                    coerce_direction(v2))
        v3 = gp_Vec()
        if derivative == 3:
            surface.D3(u, v, p, v1, v2, v3)
            return (coerce_point(p), coerce_direction(v1),
                    coerce_direction(v2), coerce_direction(v3))
        raise ValueError("Invalid derivative")

    @property
    def face_bounds(self):
        """ Get the UV bounds of a face.

        Returns
        -------
        bounds: Tuple[float, float, float, float]
            Returns in UMin, UMax, VMin, VMax the bounding values in the
            parametric space of F.

        """
        return BRepTools.UVBounds_(self.shape, 0, 0, 0, 0)

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
            def param(i):
                return c.Value(a.Parameter(i))
        else:
            def param(i):
                return a.Value(i)
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
            The bounding box of the given shapes

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
    def start_point(self) -> Point:
        """ Get the first / start point of a TopoDS_Wire or TopoDS_Edge

        """
        wire = self.shape
        if isinstance(wire, TopoDS_Edge):
            wire = BRepBuilderAPI_MakeWire(wire).Wire()
        curve = BRepAdaptor_CompCurve(wire)
        return self.get_value_at(curve, curve.FirstParameter())

    @property
    def end_point(self) -> Point:
        """ Get the end / last point of a TopoDS_Wire or TopoDS_Edge

        """
        wire = self.shape
        if isinstance(wire, TopoDS_Edge):
            wire = BRepBuilderAPI_MakeWire(wire).Wire()
        curve = BRepAdaptor_CompCurve(wire)
        return self.get_value_at(curve, curve.LastParameter())

    @property
    def start_tangent(self) -> TupleType[Point, Direction]:
        """ Get the start tangent point and direction

        """
        wire = self.shape
        if isinstance(wire, TopoDS_Edge):
            wire = BRepBuilderAPI_MakeWire(wire).Wire()
        curve = BRepAdaptor_CompCurve(wire)
        return self.get_value_at(curve, curve.FirstParameter(), 1)

    @property
    def end_tangent(self) -> TupleType[Point, Direction]:
        """ Get the end tangent point and direction

        """
        wire = self.shape
        if isinstance(wire, TopoDS_Edge):
            wire = BRepBuilderAPI_MakeWire(wire).Wire()
        curve = BRepAdaptor_CompCurve(wire)
        return self.get_value_at(curve, curve.LastParameter(), 1)

    @property
    def outer_wire(self) -> Optional[TopoDS_Wire]:
        """ If the shape is a face, return the most outer wire, otherwise None.

        Returns
        -------
        outer_wire: TopoDS_Wire
            The outer wire of the face

        """
        if isinstance(self.shape, TopoDS_Face):
            return BRepTools.OuterWire_(self.shape)
        return None

    # -------------------------------------------------------------------------
    # Shape Properties
    # -------------------------------------------------------------------------

    @property
    def length(self):
        props = GProp_GProps()
        BRepGProp.LinearProperties_(self.shape, props, True)
        return props.Mass()  # Don't ask

    mass = length

    @property
    def center_point(self) -> Point:
        """ Return the center point of this shape as computed by the bounding
        box.

        """
        return Topology.bbox(shapes=[self.shape]).center

    @property
    def area(self) -> float:
        """ Compute the area of the surface. It may be negative indicating
        the direction is reversed.

        Returns
        -------
        area: float
            The area of the surface.

        """
        props = GProp_GProps()
        BRepGProp.SurfaceProperties_(self.shape, props, True)
        return props.Mass()

    @property
    def volume(self) -> float:
        """ Volume of a solid.

        Properties
        ----------

        """
        props = GProp_GProps()
        BRepGProp.VolumeProperties_(self.shape, props, True)
        return props.Mass()

    # -------------------------------------------------------------------------
    # Intersection
    # -------------------------------------------------------------------------
    def intersection(self, shape: TopoDS_Shape) -> Optional[ListType[TopoDS_Shape]]:
        """ Returns the resulting intersection of this and the given shape
        or None if an error or there are no intersections.

        Parameters
        ----------
        shape: TopoDS_Shape
            The shape to intersect with

        Returns
        -------
        results: Optional[List[TopoDS_Shape]]
            The list of intersections.

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

    # -------------------------------------------------------------------------
    # Distances
    # -------------------------------------------------------------------------
    def min_distance_between(
        self,
        other_shape: Union[Point, TopoDS_Shape]
    ) -> float:
        return self.distance_between(other_shape, 'min').Value()

    def max_distance_between(
        self,
        other_shape: Union[Point, TopoDS_Shape]
    ) -> float:
        return self.distance_between(other_shape, 'max').Value()

    def distance_between(
        self,
        other_shape: Union[Point, TopoDS_Shape],
        min_max: str = 'min'
    ) -> float:
        """ Compute the min and max distance between this and the other shape.

        Returns
        -------
        result: BRepExtrema_DistShapeShape
            The object

        """
        if isinstance(other_shape, Point):
            other_shape = BRepBuilderAPI_MakeVertex(other_shape.proxy).Vertex()
        if min_max == 'min':
            flag = Extrema_ExtFlag_MIN
        else:
            flag = Extrema_ExtFlag_MAX
        r = BRepExtrema_DistShapeShape(self.shape, other_shape, flag)
        r.SetMultiThread(True)
        r.Perform()
        return r

