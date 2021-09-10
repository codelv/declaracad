"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""
import warnings
from atom.api import Atom, Typed, Instance
try:
    from pychrono.core import (
        ChSystem,
        ChSystemNSC,
        ChSystemSMC,
        ChVectorD,
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
    )
    from pychrono.fea import (
        ChMesh,
        ChNodeFEAbase,
        ChNodeFEAxyz,
        ChNodeFEAxyzD,
        ChNodeFEAxyzDD,
        ChNodeFEAxyzP,
        ChNodeFEAxyzrot,
        ChElementBar,
        ChElementBase,
        ChElementBeam,
        ChElementBeamANCF,
        ChElementBeamEuler,
        ChElementBeamIGA,
        ChElementBrick,
        ChElementBrick_9,
        ChElementCableANCF,
        ChElementCorotational,
        ChElementGeneric,
        ChElementHexa_20,
        ChElementHexa_8,
        ChElementHexahedron,
        ChElementShell,
        ChElementShellANCF,
        ChElementShellANCF_8,
        ChElementShellBST,
        ChElementShellReissner4,
        ChElementSpring,
        ChElementTetra_10,
        ChElementTetra_4,
        ChElementTetra_4_P,
        ChElementTetrahedron,

        ChContinuumElastic,
    )
except ImportError as e:
    warnings.warn(e)
    fea = None

from OCCT.MeshVS import MeshVS_Mesh

from declaracad.fea.analysis import ProxyAnalysis, Analysis
from declaracad.occ.api import Mesh, Point
from declaracad.occ.impl.occ_shape import OccDependentShape
from declaracad.occ.impl.occ_mesh import OccNode, OccElement, OccMeshTopology
from declaracad.core.utils import log, log_time


SYSTEM_TYPES = {
    'NSC': ChSystemNSC,
    'SMC': ChSystemSMC,
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
    "Bar": ChElementBar,
    "Base": ChElementBase,
    "Beam": ChElementBeam,
    "BeamANCF": ChElementBeamANCF,
    "BeamEuler": ChElementBeamEuler,
    "BeamIGA": ChElementBeamIGA,
    "Brick": ChElementBrick,
    "Brick_9": ChElementBrick_9,
    "CableANCF": ChElementCableANCF,
    "Corotational": ChElementCorotational,
    "Generic": ChElementGeneric,
    "Hexa_20": ChElementHexa_20,
    "Hexa_8": ChElementHexa_8,
    "Hexahedron": ChElementHexahedron,
    "Shell": ChElementShell,
    "ShellANCF": ChElementShellANCF,
    "ShellANCF_8": ChElementShellANCF_8,
    "ShellBST": ChElementShellBST,
    "ShellReissner4": ChElementShellReissner4,
    "Spring": ChElementSpring,
    "Tetra_10": ChElementTetra_10,
    "Tetra_4": ChElementTetra_4,
    "Tetra_4_P": ChElementTetra_4_P,
    "Tetrahedron": ChElementTetrahedron,
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
            element = ChElementTetra_4()
        elif n == 2:
            element = ChElementSpring()
        elif n == 8:
            element = ChElementHexa_8()
        elif n == 10:
            element = ChElementTetra_10()
        elif n == 20:
            element = ChElementHexa_20()
        elif n == 20:
            element = ChElementHexa_20()
        else:
            log.warning(f"Element with n={n} nodes={d.nodes}")
            return
        element.SetNodes(*(n.proxy.fea_node.chrono_node for n in d.nodes))
        return element

    def set_material(self, material):
        self.chrono_element.SetMaterial(material)


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
            solve = getattr(system, f'Do{solution}')
            solve()

        with log_time("Processing solution..."):
            d.process_solution(system, solver, source, mesh)

    def _default_ais_shape(self):
        return self.source.proxy.ais_shape

    def destroy(self):
        """ Cleanup resources

        """
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
