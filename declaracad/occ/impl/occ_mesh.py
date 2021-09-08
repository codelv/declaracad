"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
import os
import time
import warnings
from atom.api import Typed, ForwardTyped
from typing import Iterator
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
    MeshVS_Mesh, MeshVS_MeshPrsBuilder, MeshVS_NodalColorPrsBuilder,
    MeshVS_ElementalColorPrsBuilder,
    MeshVS_DA_MarkerColor, MeshVS_DA_MarkerScale,  MeshVS_DA_DisplayNodes,
    MeshVS_DA_MarkerType, MeshVS_DA_ShowEdges, MeshVS_DA_EdgeColor,
    MeshVS_DA_EdgeWidth, MeshVS_DA_BeamColor, MeshVS_DA_BeamWidth,
    MeshVS_DA_BeamType, MeshVS_DA_InteriorColor, MeshVS_DA_BackInteriorColor,
    MeshVS_DA_ColorReflection,
)
from OCCT.TColStd import TColStd_MapIteratorOfPackedMapOfInteger
from .occ_shape import OccShape, OccDependentShape
from .occ_draw import MARKERS
from .utils import color_to_quantity_color
from ..mesh import Shape, Node, ProxyMesh, ProxyIterator, ProxyMeshTopology

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


class OccNodeIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)

    def __iter__(self):
        mesh = self.mesh
        d = mesh.declaration
        vs_link = mesh.vs_link
        it = TColStd_MapIteratorOfPackedMapOfInteger(vs_link.GetAllNodes())
        find = vs_link.FindNode
        while it.More():
            k = it.Key()
            node = find(k)
            yield Node(id=k, x=node.X(), y=node.Y(), z=node.Z(),
                       proxy=node, mesh=d)
            it.Next()

    def __len__(self):
        return self.mesh.mesh.NbNodes()

    def __getitem__(self, key):
        node = self.mesh.vs_link.FindNode(key)
        return Node(
            id=key, x=node.X(), y=node.Y(), z=node.Z(),
            proxy=node, mesh=self.mesh.declaration)


class OccElementIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)

    def __iter__(self):
        vs_link = self.mesh.vs_link
        it = TColStd_MapIteratorOfPackedMapOfInteger(vs_link.GetAllElements())
        find = vs_link.FindElement
        while it.More():
            yield find(it.Key())
            it.Next()

    def __len__(self):
        return self.mesh.mesh.NbElements()

    def __getitem__(self, key):
        return self.mesh.vs_link.FindElement(key)


class OccMeshTopology(ProxyMeshTopology):
    mesh = ForwardTyped(lambda: OccMesh)

    def _get_node_iterator(self) -> OccNodeIterator:
        return OccNodeIterator(mesh=self.mesh)

    def _get_element_iterator(self) -> OccElementIterator:
        return OccElementIterator(mesh=self.mesh)

    def _get_link_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    #def _get_face_iterator(self) -> ProxyIterator:
        #raise NotImplementedError

    #def _get_volume_iterator(self) -> ProxyIterator:


    #def _get_group_iterator(self) -> ProxyIterator:
    #    raise OccGroupIterator(mesh=self.mesh)



class OccMesh(OccDependentShape, ProxyMesh):
    """ Implementation is based on pySMESH by trelau

    """
    builder = Typed(MeshVS_MeshPrsBuilder)
    node_builder = Typed(MeshVS_NodalColorPrsBuilder)
    element_builder = Typed(MeshVS_ElementalColorPrsBuilder)
    ais_shape = Typed(MeshVS_Mesh)
    gen = Typed(SMESH_Gen)
    mesh = Typed(SMESH_Mesh)
    vs_link = Typed(SMESH_MeshVSLink)
    topology = Typed(OccMeshTopology)

    def _default_topology(self):
        if self.ais_shape is None:
            self.declaration.render()  # Force build the shape
        return OccMeshTopology(mesh=self)

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
            t = time.time()
            log.debug("Computing mesh...")
            result = gen.Compute(mesh, mesh.GetShapeToMesh())
            if not result:
                raise RuntimeError(f"Failed to mesh {d}: {result}")
            log.debug("Done! ({}ms)".format(round((time.time()-t)/1000, 2)))

            #if d.group:
            #    vs_link = SMESH_MeshVSLink(mesh, d.group)
            #else:
            vs_link = self.vs_link = SMESH_MeshVSLink(mesh)
            mesh_vs.SetDataSource(vs_link)
            builder = self.builder = MeshVS_MeshPrsBuilder(mesh_vs)
            node_builder = self.node_builder = MeshVS_NodalColorPrsBuilder(
                mesh_vs, 3 | 8, vs_link, 1)
            element_builder = self.element_builder = MeshVS_ElementalColorPrsBuilder(
                mesh_vs, 3 | 10, vs_link, 2)
            d.process_mesh()
            self.update_style()
            log.debug("Colorizing mesh...")
            d.colorize_mesh()
            log.debug("Done!")
            mesh_vs.AddBuilder(builder, True)
            mesh_vs.AddBuilder(node_builder)
            mesh_vs.AddBuilder(element_builder)
            mesh_vs.SetDisplayMode(2)  # Shaded
            mesh_vs.UpdateSelectableNodes()
            #mesh_vs.SetMeshSelMethod(30)

            if d.export_filename:
                self.export(d.export_filename, d.export_type)

        self.shape = fixed_shape

    def update_style(self):
        d = self.declaration
        drawer = self.ais_shape.GetDrawer()
        # Nodes
        if d.node_color:
            c, t = color_to_quantity_color(d.node_color)
            drawer.SetColor(MeshVS_DA_MarkerColor, c)
            drawer.SetDouble(MeshVS_DA_MarkerScale, d.node_size)
            drawer.SetBoolean(MeshVS_DA_DisplayNodes, True)
            drawer.SetInteger(MeshVS_DA_MarkerType, MARKERS[d.node_type])
        else:
            drawer.SetBoolean(MeshVS_DA_DisplayNodes, False)

        if d.edge_color:
            c, t = color_to_quantity_color(d.edge_color)
            drawer.SetColor(MeshVS_DA_EdgeColor, c)
            drawer.SetDouble(MeshVS_DA_EdgeWidth, d.edge_size)
            drawer.SetBoolean(MeshVS_DA_ShowEdges, True)
        else:
            drawer.SetBoolean(MeshVS_DA_ShowEdges, False)

        if d.beam_color:
            c, t = color_to_quantity_color(d.beam_color)
            drawer.SetColor(MeshVS_DA_BeamColor, c)
            drawer.SetDouble(MeshVS_DA_BeamWidth, d.beam_size)

        if d.color:
            c, t = color_to_quantity_color(d.color)
            drawer.SetColor(MeshVS_DA_InteriorColor, c)
        drawer.SetBoolean(MeshVS_DA_ColorReflection, True)

    def export(self, filename, export_type, *args):
        """ Export the mesh. The extension is added automatically

        Parameters
        ----------
        filename: String
            The base filename (excluding the extension)
        export_type: String
            The export type. Must map to one of the Export functions

        """
        d = self.declaration
        filename = os.path.abspath(filename)
        filename = f'{filename}.{export_type.lower()}'
        log.info(f"Exporting mesh to '{filename}'")
        export = getattr(self.mesh, f'Export{export_type.upper()}')
        if export_type == 'stl' and not args:
            args = [True]  # Use ascii
        export(filename, *args)
        log.info("Ok!")

    def _default_ais_shape(self):
        return self.mesh_vs

    def set_source(self, source):
        self.update_shape()

    def set_algorithm(self, algo):
        self.update_shape()

    def set_node_color(self, index, color):
        c, _ = color_to_quantity_color(color)
        self.node_builder.SetColor(index, c)

    def set_element_color(self, index, front_color, back_color=None):
        front, _ = color_to_quantity_color(front_color)
        if back_color is None:
            self.element_builder.SetColor1(index, front)
        else:
            back, _ = color_to_quantity_color(back_color)
            self.element_builder.SetColor2(index, front, back)
