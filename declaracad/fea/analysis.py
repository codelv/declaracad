"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""

from typing import Any

from atom.api import Bool, Coerced, Enum, ForwardTyped, Value, observe
from enaml.core.declarative import d_, d_func

from declaracad.occ.shape import Direction, ProxyShape, Shape, coerce_direction


class ProxyAnalysis(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Analysis)

    def set_source(self, source):
        raise NotImplementedError

    def set_gravity(self, gravity: Direction):
        raise NotImplementedError


class Analysis(Shape):
    """A finite element analysis block."""

    #: Disable analysis
    disabled = d_(Bool())

    #: System type (non-smooth contact or smooth contact)
    system_type = d_(Enum("NSC", "SMC"))

    #: Solver type
    solver_type = d_(
        Enum(
            "ADMM",
            "APGD",
            "BB",
            "BiCGSTAB",
            "GMRES",
            "LS",
            "MINRES",
            "PJacobi",
            "PSOR",
            "SparseLU",
            "SparseQR",
            "VI",
        )
    )

    #: Solution method
    solution_type = d_(
        Enum(
            "static-linear",
            "static-nonlinear",
            "static-nonlinear-rheonomic",
        )
    )

    #: Mesh to perform analysis on
    source = d_(Value())

    #: Direction of gravity. The default is in the -Z direction.
    gravity = d_(Coerced(Direction, coercer=coerce_direction))

    def _default_gravity(self):
        return Direction(0, 0, -9.8)

    @d_func
    def create_material(self):
        """ """
        pass

    @d_func
    def prepare_system(self, system, solver, source, mesh):
        """Prepare the mesh for analysis. You can add constraints, etc
        set forces on the nodes etc here.

        """
        pass

    @d_func
    def process_solution(self, system, solver, source, mesh):
        """Do something with the solution"""
        pass

    @observe("gravity")
    def _update_proxy(self, change: dict[str, Any]):
        super()._update_proxy(change)
