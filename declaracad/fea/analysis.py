"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""
import warnings
from atom.api import (
    Atom, Value, Typed, ForwardTyped, Enum, Dict, Bool, Float, Property,
    Str, Int
)
from enaml.core.declarative import d_, d_func
from enaml.colors import ColorMember
from declaracad.occ.shape import ProxyShape, Shape
from declaracad.occ.mesh import Node as MeshNode


class ProxyAnalysis(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Analysis)

    def set_source(self, source):
        raise NotImplementedError


class Analysis(Shape):
    """ A finite element analysis block

    """

    #: System type (non-smooth contact or smooth contact)
    system_type = d_(Enum('NSC', 'SMC'))

    #: Solver type
    solver_type = d_(Enum(
        'ADMM', 'APGD', 'BB', 'BiCGSTAB', 'GMRES', 'LS',
        'MINRES', 'PJacobi', 'PSOR', 'SparseLU', 'SparseQR', 'VI'
    ))

    #: Solution method
    solution_type = d_(Enum(
        'static-linear',
        'static-nonlinear',
        'static-nonlinear-rheonomic',
    ))

    #: Mesh to perform analysis on
    source = d_(Value())

    @d_func
    def prepare_system(self, system, solver, mesh):
        """ Prepare the mesh for analysis. You can add constraints, etc

        """
        pass

    @d_func
    def process_solution(self, system, solver, mesh):
        """ Do something with the solution

        """
        pass

