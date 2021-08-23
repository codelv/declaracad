"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
from atom.api import Value, Typed, ForwardTyped, Enum, Dict, Bool
from enaml.core.declarative import d_, d_func
from .shape import ProxyShape, Shape


class ProxyMesh(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Mesh)

    def set_source(self, source):
        raise NotImplementedError

    def set_disabled(self, disabled):
        raise NotImplementedError


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
