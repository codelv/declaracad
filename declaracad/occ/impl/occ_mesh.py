"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
import warnings
from atom.api import Typed
from OCCT.BRepCheck import BRepCheck_Analyzer
from OCCT.BRepMesh import (
    BRepMesh_Context,
    BRepMesh_FaceDiscret,
    BRepMesh_IncrementalMesh,
    BRepMesh_DelabellaMeshAlgoFactory
)
from OCCT.ShapeBuild import ShapeBuild_ReShape
from OCCT.ShapeFix import ShapeFix_Shape, ShapeFix_ShapeTolerance
from OCCT.MeshVS import (
    MeshVS_Mesh, MeshVS_MeshPrsBuilder, MeshVS_DrawerAttribute
)

from .occ_shape import OccShape, OccDependentShape
from ..mesh import Shape, ProxyMesh

from declaracad.core.utils import log

try:
    from SMESH.SMDSAbs import SMDSAbs_Node
    from SMESH.SMESH import (
        SMESH_MeshVSLink, SMESH_Mesh, SMESH_subMesh, SMESH_Gen
    )
    from SMESH.NETGENPlugin import (
        NETGENPlugin_SimpleHypothesis_3D, NETGENPlugin_NETGEN_2D3D
    )
except ImportError as e:
    warnings.log(e)

    # Dummy imports
    SMESH_Gen = object
    SMESH_Mesh = object
    SMESH_MeshVSLink = object


class OccMesh(OccDependentShape, ProxyMesh):
    """ Implementation is based on pySMESH by trelau

    """
    builder = Typed(MeshVS_MeshPrsBuilder)
    ais_shape = Typed(MeshVS_Mesh)
    gen = Typed(SMESH_Gen)
    mesh = Typed(SMESH_Mesh)
    vs_link = Typed(SMESH_MeshVSLink)

    def update_shape(self, change=None):
        d = self.declaration

        source = None
        if d.source:
            source = d.source
            if isinstance(source, Shape):
                source = source.proxy.shape
        else:
            child = self.get_first_child()
            source = child.shape

        gen = self.gen = SMESH_Gen()
        mesh = self.mesh = gen.CreateMesh(True)
        mesh_vs = self.ais_shape = MeshVS_Mesh()

        # Cleanup shape
        fixer = ShapeFix_Shape(source)
        result = fixer.Perform()
        #if not fixer.Perform():
        #    raise RuntimeError(f"Failed to fix {source}")
        fixed_shape = fixer.Shape()

        if not d.disabled:
            mesh.ShapeToMesh(fixed_shape)
            d.prepare_mesh(gen, mesh, fixed_shape)
            result = gen.Compute(mesh, mesh.GetShapeToMesh())
            if not result:
                raise RuntimeError(f"Failed to mesh {d}: {result}")

            #if d.group:
            #    vs_link = SMESH_MeshVSLink(mesh, d.group)
            #else:
            vs_link = self.vs_link = SMESH_MeshVSLink(mesh)

            mesh_vs.SetDataSource(vs_link)
            builder = self.builder = MeshVS_MeshPrsBuilder(mesh_vs)
            mesh_vs.AddBuilder(builder)
            mesh_vs.SetDisplayMode(2)
            #drawer = mesh.GetDrawer()
        self.shape = fixed_shape

    def _default_ais_shape(self):
        return self.mesh_vs

    def set_source(self, source):
        self.update_shape()

    def set_algorithm(self, algo):
        self.update_shape()
