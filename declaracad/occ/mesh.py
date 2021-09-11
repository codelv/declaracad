"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
from typing import Optional
from atom.api import (
    Atom, Value, Typed, ForwardTyped, Enum, Dict, Bool, Float, Property,
    List, Str, Int, Coerced, observe
)
from enaml.core.declarative import d_, d_func
from enaml.colors import Color, ColorMember
from .shape import (
    ProxyShape, Shape, Point, Direction, coerce_direction, coerce_point
)


class ProxyNode(Atom):
    declaration = ForwardTyped(lambda: Node)

    def set_position(self, position):
        raise NotImplementedError

    def set_color(self, color):
        raise NotImplementedError

    def set_mass(self, mass):
        raise NotImplementedError

    def set_force(self, force):
        raise NotImplementedError

    def set_torque(self, torque):
        raise NotImplementedError

    def set_fixed(self, fixed):
        raise NotImplementedError

    def get_displaced_position(self):
        raise NotImplementedError


class ProxyElement(Atom):
    declaration = ForwardTyped(lambda: Element)

    def set_front_color(self, color):
        raise NotImplementedError

    def set_back_color(self, color):
        raise NotImplementedError


class ProxyMesh(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Mesh)

    def find_node(self, id) -> 'Node':
        raise NotImplementedError

    def find_element(self, id) -> 'Element':
        raise NotImplementedError

    def find_element(self, id) -> 'Element':
        raise NotImplementedError

    def find_face(self, id) -> 'Element':
        raise NotImplementedError

    def find_volume(self, id) -> 'Element':
        raise NotImplementedError

    def set_source(self, source):
        raise NotImplementedError

    def set_disabled(self, disabled):
        raise NotImplementedError


class ProxyIterator(Atom):
    """ Mesh item iterator

    """
    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __getitem__(self, key):
        raise NotImplementedError


class ProxyMeshTopology(Atom):
    #: Reference to the mesh
    declaration = ForwardTyped(lambda: Mesh)

    def _get_node_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_element_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_link_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_face_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_volume_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_group_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    #: Node iterator
    nodes = Property(lambda s: s._get_node_iterator())

    #: Elements iterator
    elements = Property(lambda s: s._get_element_iterator())

    #: Links
    links = Property(lambda s: s._get_link_iterator())

    #: Faces iterator
    faces = Property(lambda s: s._get_face_iterator())

    #: Volumes iterator
    volumes = Property(lambda s: s._get_volume_iterator())

    #: Groups iterator
    groups = Property(lambda s: s._get_group_iterator())


class Node(Atom):
    """ A mesh node.

    This is meant to be used as a pass through object.

    """
    #: Proxy to the internal object
    proxy = Typed(ProxyNode)

    #: The mesh this node is connected to
    mesh = ForwardTyped(lambda: Mesh)

    #: ID within the mesh
    id = Int()

    #: Color of the node
    color = ColorMember()

    #: Description displayed when selected
    description = Str()

    #: Mass of the node
    mass = Float(strict=False)

    #: Position of the node
    position = Coerced(Point, coercer=coerce_point)

    #: Displaced position
    def _get_displaced_position(self):
        return self.proxy.get_displaced_position()

    #: Displaced position after analysis
    displaced_position = Property(_get_displaced_position)

    def _get_displacement(self):
        return self.displaced_position - self.position

    #: Get the delta between the original position and the displaced position
    displacement = Property(_get_displacement)

    #: Force acting on the node
    force = Coerced(Direction, coercer=coerce_direction)

    #: Torque acting on the node
    torque = Coerced(Direction, coercer=coerce_direction)

    #: Position is fixed
    fixed = Bool()

    #: Member to store any relevent data
    data = Dict()

    @observe('color', 'mass', 'position', 'force', 'torque', 'fixed')
    def _update_proxy(self, change):
        setter = getattr(self.proxy, 'set_%s' % change['name'])
        setter(change['value'])

    def __repr__(self):
        return "<Node: x=%s y=%s z=%s>" % self.position[:]


class Element(Atom):
    #: Proxy to the internal object
    proxy = Typed(ProxyElement)

    #: Set of nodes that make up this element
    nodes = List(Node)

    #: The mesh this node is connected to
    mesh = ForwardTyped(lambda: Mesh)

    #: ID within the mesh
    id = Int()

    #: Description displayed when selected
    description = Str()

    #: Front color of the node
    front_color = ColorMember()

    #: Back color of the node
    back_color = ColorMember()

    #: Material definition
    material = ForwardTyped(lambda: Material)

    #: Member to store any relevent data
    data = Dict()

    @observe('front_color', 'back_color')
    def _update_proxy(self, change):
        setter = getattr(self.proxy, 'set_%s' % change['name'])
        setter(change['value'])


class Material(Atom):
    #: The internal object
    proxy = Value()

    #: Density of the material in Kg/m^2
    density = Float()

    #: Youngs E elastic modulus in PA (N/m^2)
    e = Float()

    #: Posson V ratio
    v = Float()

    #: Shear modulus in PA (N/m^2)
    g = Float()

    #: Rayleigh damping
    m = Float()

    #: Rayleigh stiffness
    k = Float()


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

    #: May be either a shape to mesh or a numpy array
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

    # ---------------------------------------------------------------------
    # Mesh API
    # ---------------------------------------------------------------------
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
    def process_mesh(self):
        """ Process the generated mesh. This is invoked before colorizing.

        If you want to use your own FEA, this is a good place to hook in.

        """
        pass

    @d_func
    def colorize_mesh(self):
        """ This is invoked after the mesh is computed. The topology can
        be used to apply colors to nodes and elements.

        """
        pass

    # ---------------------------------------------------------------------
    # Mesh lookup API
    # ---------------------------------------------------------------------
    def find_node(self, id) -> Node:
        """ Find the node with the given ID.

        """
        return self.proxy.find_node(id)

    def find_element(self, id) -> Element:
        """ Find the node with the given ID.

        """
        return self.proxy.find_element(id)

    def find_face(self, id) -> Element:
        """ Find the face element with the given ID.

        """
        return self.proxy.find_face(id)

    def find_volume(self, id) -> Element:
        """ Find the volume element with the given ID.

        """
        return self.proxy.find_volume(id)
