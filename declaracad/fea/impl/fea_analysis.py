"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""

import warnings

from atom.api import Atom, Instance, Typed

try:
    from pychrono import fea
    from pychrono.core import (
        ChSolver,
        ChSolverADMM,
        ChSolverAPGD,
        ChSolverBB,
        ChSolverBiCGSTAB,
        ChSolverGMRES,
        ChSolverLS,
        ChSolverMINRES,
        ChSolverPJacobi,
        ChSolverPSOR,
        ChSolverSparseLU,
        ChSolverSparseQR,
        ChSolverVI,
        ChSystem,
        ChSystemNSC,
        ChSystemSMC,
        ChVectorD,
    )
    from pychrono.fea import (
        ChContinuumElastic,
        ChElementBase,
        ChElementHexaANCF_3813_9,
        ChElementHexaCorot_8,
        ChElementHexaCorot_20,
        ChElementSpring,
        ChElementTetraCorot_4,
        ChElementTetraCorot_10,
        ChMesh,
        ChNodeFEAbase,
        ChNodeFEAxyz,
        ChNodeFEAxyzD,
        ChNodeFEAxyzDD,
        ChNodeFEAxyzP,
        ChNodeFEAxyzrot,
    )
except ImportError as e:
    warnings.warn(f"{e}")
    fea = None

from OCCT.MeshVS import MeshVS_Mesh

from declaracad.core.utils import log, log_time
from declaracad.fea.analysis import ProxyAnalysis
from declaracad.occ.api import Mesh, Point
from declaracad.occ.impl.occ_mesh import OccElement, OccMeshTopology, OccNode
from declaracad.occ.impl.occ_shape import OccDependentShape

SYSTEM_TYPES = {
    "NSC": ChSystemNSC,
    "SMC": ChSystemSMC,
}


SOLVER_TYPES = {
    "ADMM": ChSolverADMM,
    "APGD": ChSolverAPGD,
    "BB": ChSolverBB,
    "BiCGSTAB": ChSolverBiCGSTAB,
    "GMRES": ChSolverGMRES,
    "LS": ChSolverLS,
    "MINRES": ChSolverMINRES,
    "PJacobi": ChSolverPJacobi,
    "PSOR": ChSolverPSOR,
    "SparseLU": ChSolverSparseLU,
    "SparseQR": ChSolverSparseQR,
    "VI": ChSolverVI,
}


NODE_TYPES = {
    "xyz": ChNodeFEAxyz,
    "xyzD": ChNodeFEAxyzD,
    "xyzDD": ChNodeFEAxyzDD,
    "xyzP": ChNodeFEAxyzP,
    "xyzrot": ChNodeFEAxyzrot,
}


ELEMENT_TYPES = {
    e[9:]: getattr(fea, e)
    for e in dir(fea)
    if e.startswith("ChElement") and not e.endswith("swigregister")
}


class FeaNode(Atom):
    occ_node = Typed(OccNode)
    chrono_node = Instance(ChNodeFEAbase)

    def _default_chrono_node(self):
        # TODO: Determine type???
        d = self.occ_node.declaration
        return ChNodeFEAxyz(ChVectorD(*d.position))

    def set_fixed(self, fixed):
        self.chrono_node.SetFixed(fixed)

    def set_mass(self, mass):
        self.chrono_node.SetMass(mass)

    def set_force(self, force):
        self.chrono_node.SetForce(ChVectorD(*force))

    def set_torque(self, torque):
        self.chrono_node.SetTorque(ChVectorD(*torque))

    def get_displaced_position(self):
        p = self.chrono_node.GetPos()
        return Point(p.x, p.y, p.z)


class FeaElement(Atom):
    occ_element = Typed(OccElement)
    chrono_element = Typed(ChElementBase)

    def _default_chrono_element(self):
        d = self.occ_element.declaration
        n = len(d.nodes)
        if n == 4:
            element = ChElementTetraCorot_4()
        elif n == 2:
            element = ChElementSpring()
        elif n == 8:
            element = ChElementHexaCorot_8()
        elif n == 9:
            element = ChElementHexaANCF_3813_9()
        elif n == 10:
            element = ChElementTetraCorot_10()
        elif n == 20:
            element = ChElementHexaCorot_20()
        else:
            log.warning(f"Element with n={n} nodes={d.nodes}")
            return
        element.SetNodes(*(n.proxy.fea_node.chrono_node for n in d.nodes))
        return element

    def set_material(self, material):
        self.chrono_element.SetMaterial(material)

    def get_stress(self):
        stress = self.chrono_element.GetStress()
        return stress.GetEquivalentVonMises()

    def get_strain(self):
        strain = self.chrono_element.GetStrain()
        return strain.GetEquivalentVonMises()


class FeaAnalysis(OccDependentShape, ProxyAnalysis):
    ais_shape = Typed(MeshVS_Mesh)
    source = Typed(Mesh)
    system = Instance(ChSystem)
    solver = Instance(ChSolver)
    mesh = Typed(ChMesh)

    def _default_topology(self):
        if self.ais_shape is None:
            self.declaration.render()
        return self.source.topology

    #: Proxy to source mesh
    topology = Typed(OccMeshTopology)

    def _default_source(self):
        d = self.declaration
        if d.source:
            return d.source
        else:
            return self.get_first_child()

    def update_shape(self, change=None):
        d = self.declaration
        source = self._default_source()

        System = SYSTEM_TYPES[d.system_type]
        system = self.system = System()
        mesh = self.mesh = ChMesh()
        system.Add(mesh)
        system.Set_G_acc(ChVectorD(*d.gravity))

        Solver = SOLVER_TYPES[d.solver_type]
        solver = self.solver = Solver()
        system.SetSolver(solver)

        if not d.disabled:
            self.do_analysis(source)

        # Add each element to the mesh
        self.shape = source.proxy.shape

    def do_analysis(self, source):
        d = self.declaration
        system = self.system
        solver = self.solver
        mesh = self.mesh
        with log_time("Preparing system..."):
            d.prepare_system(system, solver, source, mesh)

        #: TODO...
        material = d.create_material()
        if material is None:
            material = ChContinuumElastic()
            material.Set_E(207e6)
            material.Set_v(0.3)

        # Add each node to the mesh
        with log_time("Generating FEA mesh..."):
            for node in source.topology.nodes:
                mesh.AddNode(node.proxy.fea_node.chrono_node)

            #: Create element f0r each
            for element in source.topology.volumes:
                e = element.proxy.fea_element
                if e.chrono_element:
                    e.set_material(material)
                    mesh.AddElement(e.chrono_element)

        with log_time("Running FEA..."):
            solution = d.solution_type.title().replace("-", "")
            solve = getattr(system, f"Do{solution}")
            solve()

        with log_time("Processing solution..."):
            d.process_solution(system, solver, source, mesh)

    def _default_ais_shape(self):
        return self.source.proxy.ais_shape

    def destroy(self):
        """Cleanup resources"""
        super().destroy()
        if self.mesh:
            del self.mesh
        if self.solver:
            del self.solver
        if self.system:
            del self.system

    # ------------------------------------------------------------------------
    # ProxyAnalysis API
    # ------------------------------------------------------------------------
    def set_source(self, source):
        self.update_shape()

    def set_gravity(self, gravity):
        self.system.Set_G_acc(ChVectorD(*gravity))
