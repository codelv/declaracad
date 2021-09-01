"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
from atom.api import (
    Atom, Value, Typed, ForwardTyped, Enum, Dict, Bool, Float, Property,
    Str, Int
)
from enaml.core.declarative import d_, d_func
from enaml.colors import ColorMember
from .shape import ProxyShape, Shape


class ProxyMesh(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Mesh)

    def set_source(self, source):
        raise NotImplementedError

    def set_disabled(self, disabled):
        raise NotImplementedError

    def set_node_color(self, index, color):
        raise NotImplementedError

    def set_element_color(self, index, front_color, back_color=None):
        raise NotImplementedError


class ProxyMeshTopology(Atom):
    #: Reference to the mesh
    declaration = ForwardTyped(lambda: Mesh)

    # ------------------------------------------------------------------
    # Proxy API
    # ------------------------------------------------------------------
    def _get_nodes(self):
        raise NotImplementedError

    def _get_elements(self):
        raise NotImplementedError

    def _get_faces(self):
        raise NotImplementedError

    def _get_volumes(self):
        raise NotImplementedError

    def _get_groups(self):
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Pubilc API
    # ------------------------------------------------------------------
    #: Node iterator
    nodes = Property(lambda s: s._get_nodes())

    #: Number of nodes
    node_count = Int()

    #: Elements iterator
    elements = Property(lambda s: s._get_elements())

    #: Number of edges
    edge_count = Int()

    #: Faces iterator
    faces = Property(lambda s: s._get_faces())

    #: Number of faces
    face_count = Int()

    #: Volumes iterator
    volumes = Property(lambda s: s._get_volumes())

    #: Number of volumes
    volume_count = Int()

    #: Groups iterator
    groups = Property(lambda s: s._get_groups())


class Mesh(Shape):
    """ A Mesh

    Attributes
    ----------

    source: Shape
        Either a shape to mesh or a datasource.
        Alternatively the shape can be nested.
    algorithm: String
        The meshing algorithm to use to generate the mesh.

    Examples
    --------

    enamldef Case(Part):
        Box: box:
            pass
        Mesh:
            source = box


    """
    proxy = Typed(ProxyMesh)

    #: Shape to mesh
    source = d_(Value())

    #: Meshing options
    options = d_(Dict())

    #: Disable meshing
    disabled = d_(Bool())

    #: Export type
    export_type = d_(Enum('med', 'dat', 'unv', 'stl', 'cgns', 'gmf', 'sauv'))

    #: If given, write the mesh to a file
    export_filename = d_(Str())

    # ---------------------------------------------------------------------
    # Mesh display parameters
    # ---------------------------------------------------------------------
    node_color = d_(ColorMember())
    node_size = d_(Float(1.0, strict=False))
    node_type = d_(Enum(
        'circle', 'ball', 'dot', 'plus', 'point', 'star', 'cross',
        'point-in-circle', 'star-in-circle',
        'plus-in-circle', 'cross-in-circle',
        'large-ring', 'medium-ring', 'small-ring'))

    edge_color = d_(ColorMember("grey"))
    edge_size = d_(Float(1.0, strict=False))

    beam_color = d_(ColorMember('black'))
    beam_size = d_(Float(1.0, strict=False))

    @d_func
    def prepare_mesh(self, gen, mesh, shape):
        """ This is invoked before the mesh is computed. It should be
        defined to prepare the meshing parameters.

        Parameters
        ----------
        gen: SMESH_Gen
            The mesh generator
        mesh: SMESH_Mesh
            The mesh handle
        shape: TopoDS_Shape
            The shape being meshed

        """
        raise NotImplementedError

    @d_func
    def colorize_mesh(self):
        """ This is invoked after the mesh is computed. The topology can
        be used to apply colors to nodes and elements.

        """
        pass

    def set_node_color(self, index, color):
        """ Set the the color of the given node index

        """
        self.proxy.set_node_color(index, color)

    def set_element_color(self, index, front_color, back_color=None):
        """ Set the the front and back colors of the given element index

        """
        self.proxy.set_element_color(index, front_color, back_color)
