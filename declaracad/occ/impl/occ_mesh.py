"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 3, 2021

@author: jrm
"""
import os
import warnings
from typing import Optional, Union

from atom.api import Dict, ForwardTyped, Typed
from enaml.colors import Color
from OCCT.MeshVS import (
    MeshVS_DA_BeamColor,
    MeshVS_DA_BeamWidth,
    MeshVS_DA_ColorReflection,
    MeshVS_DA_DisplayNodes,
    MeshVS_DA_EdgeColor,
    MeshVS_DA_EdgeWidth,
    MeshVS_DA_InteriorColor,
    MeshVS_DA_MarkerColor,
    MeshVS_DA_MarkerScale,
    MeshVS_DA_MarkerType,
    MeshVS_DA_ShowEdges,
    MeshVS_ElementalColorPrsBuilder,
    MeshVS_Mesh,
    MeshVS_MeshPrsBuilder,
    MeshVS_NodalColorPrsBuilder,
)
from OCCT.ShapeFix import ShapeFix_Shape
from OCCT.TColStd import TColStd_Array1OfInteger
from OCCT.TopoDS import TopoDS_Shape

from declaracad.core.utils import log, log_time
from declaracad.occ.mesh import (
    Element,
    Node,
    ProxyElement,
    ProxyIterator,
    ProxyMesh,
    ProxyMeshTopology,
    ProxyNode,
    Shape,
)
from declaracad.occ.shape import Point

from .occ_shape import OccDependentShape
from .occ_vertex import MARKERS
from .utils import color_to_quantity_color

try:
    from SMESH.SMDS import SMDS_MeshElement, SMDS_MeshNode
    from SMESH.SMESH import SMESH_Gen, SMESH_Mesh, SMESH_MeshVSLink
    from SMESH.SMESHDS import SMESHDS_Mesh
except ImportError as e:
    warnings.warn(f"{e}")

    # Dummy imports
    SMESH_Gen = object
    SMESH_Mesh = object
    SMESH_MeshVSLink = object
    SMDS_MeshNode = object
    SMDS_MeshElement = object
    SMESHDS_Mesh = object


def fea_node_type():
    from declaracad.fea.impl.fea_analysis import FeaNode

    return FeaNode


def fea_element_type():
    from declaracad.fea.impl.fea_analysis import FeaElement

    return FeaElement


# ----------------------------------------------------------------------------
# Mesh elements
# ----------------------------------------------------------------------------
class OccNode(ProxyNode):
    mesh = ForwardTyped(lambda: OccMesh)
    fea_node = ForwardTyped(fea_node_type)
    smesh_node = Typed(SMDS_MeshNode)

    def _default_fea_node(self):
        FeaNode = fea_node_type()
        return FeaNode(occ_node=self)

    def set_position(self, position):
        self.smesh_node.setXYZ(*position)

    def set_color(self, color):
        self.mesh.set_node_color(self.declaration.id, color)

    def set_mass(self, mass):
        self.fea_node.set_mass(mass)

    def set_force(self, force):
        self.fea_node.set_force(force)

    def set_torque(self, torque):
        self.fea_node.set_torque(torque)

    def set_fixed(self, fixed):
        self.fea_node.set_fixed(fixed)

    def get_displaced_position(self):
        return self.fea_node.get_displaced_position()


class OccElement(ProxyElement):
    mesh = ForwardTyped(lambda: OccMesh)
    fea_element = ForwardTyped(fea_element_type)
    smesh_element = Typed(SMDS_MeshElement)

    def _default_fea_element(self):
        FeaElement = fea_element_type()
        return FeaElement(occ_element=self)

    def set_front_color(self, color):
        d = self.declaration
        self.mesh.set_element_color(d.id, d.front_color, d.back_color)

    def set_back_color(self, color):
        self.set_front_color(color)

    def get_stress(self):
        return self.fea_element.get_stress()

    def get_strain(self):
        return self.fea_element.get_strain()


def create_node(key: int, mesh: "OccMesh", smesh_node: SMDS_MeshNode) -> Node:
    """Create a Node declaration from a generated mesh."""
    node = Node(id=key, mesh=mesh.declaration)
    node.proxy = OccNode(declaration=node, mesh=mesh, smesh_node=smesh_node)
    node.position = Point(smesh_node.X(), smesh_node.Y(), smesh_node.Z())
    return node


def create_element(
    key: int, mesh: "OccMesh", smesh_element: SMDS_MeshElement
) -> Element:
    """Create an Element declaration from a generated mesh."""
    n = smesh_element.NbNodes()
    array = TColStd_Array1OfInteger(0, n)
    mesh.vs_link.GetNodesByElement(key, array, n)
    nodes = [mesh.find_node(array.Value(i)) for i in range(1, n + 1)]
    e = Element(id=key, nodes=nodes)
    e.proxy = OccElement(declaration=e, smesh_element=smesh_element)
    return e


# ----------------------------------------------------------------------------
# Mesh topology iterators
# ----------------------------------------------------------------------------


class OccNodeIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)

    def __iter__(self):
        it = self.mesh.smesh_ds.nodesIterator()
        while it.more():
            yield self[it.next()]

    def __len__(self):
        return self.mesh.smesh_ds.NbNodes()

    def __getitem__(self, key):
        return self.mesh.find_node(key)


class OccElementIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)
    nodes = Typed(OccNodeIterator)

    def _default_nodes(self):
        return OccNodeIterator(mesh=self.mesh)

    def __iter__(self):
        it = self.mesh.smesh_ds.elementsIterator()
        while it.more():
            yield self[it.next()]

    def __len__(self):
        return self.mesh.smesh_ds.NbElements()

    def __getitem__(self, key):
        return self.mesh.find_element(key)


class OccFaceIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)
    nodes = Typed(OccNodeIterator)

    def _default_nodes(self):
        return OccNodeIterator(mesh=self.mesh)

    def __iter__(self):
        it = self.mesh.smesh_ds.facesIterator()
        while it.more():
            yield self[it.next()]

    def __len__(self):
        return self.mesh.smesh_ds.NbFaces()

    def __getitem__(self, key):
        return self.mesh.find_face(key)


class OccVolumeIterator(ProxyIterator):
    mesh = ForwardTyped(lambda: OccMesh)
    nodes = Typed(OccNodeIterator)

    def _default_nodes(self):
        return OccNodeIterator(mesh=self.mesh)

    def __iter__(self):
        it = self.mesh.smesh_ds.volumesIterator()
        while it.more():
            yield self[it.next()]

    def __len__(self):
        return self.mesh.smesh_ds.NbVolumes()

    def __getitem__(self, key):
        return self.mesh.find_volume(key)


class OccMeshTopology(ProxyMeshTopology):
    mesh = ForwardTyped(lambda: OccMesh)

    def _get_node_iterator(self) -> OccNodeIterator:
        return OccNodeIterator(mesh=self.mesh)

    def _get_element_iterator(self) -> OccElementIterator:
        return OccElementIterator(mesh=self.mesh)

    def _get_link_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_face_iterator(self) -> ProxyIterator:
        raise NotImplementedError

    def _get_volume_iterator(self) -> ProxyIterator:
        return OccVolumeIterator(mesh=self.mesh)

    # def _get_group_iterator(self) -> ProxyIterator:
    #    raise OccGroupIterator(mesh=self.mesh)


class OccMesh(OccDependentShape, ProxyMesh):
    """Implementation is based on pySMESH by trelau"""

    builder = Typed(MeshVS_MeshPrsBuilder)
    node_builder = Typed(MeshVS_NodalColorPrsBuilder)
    element_builder = Typed(MeshVS_ElementalColorPrsBuilder)
    ais_shape = Typed(MeshVS_Mesh, ())
    source = Typed(TopoDS_Shape)
    gen = Typed(SMESH_Gen, ())
    mesh = Typed(SMESH_Mesh)
    vs_link = Typed(SMESH_MeshVSLink)
    smesh_ds = Typed(SMESHDS_Mesh)
    topology = Typed(OccMeshTopology)

    #: Cached items
    nodes = Dict(int, Node)
    elements = Dict(int, Element)
    faces = Dict(int, Element)
    volumes = Dict(int, Element)

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
        self.mesh = gen.CreateMesh(True)
        self.ais_shape = MeshVS_Mesh()

        # Cleanup shape
        fixer = ShapeFix_Shape(source)
        fixer.Perform()
        # if not fixer.Perform():
        #    raise RuntimeError(f"Failed to fix {source}")
        fixed_shape = fixer.Shape()
        if not d.disabled:
            self.update_mesh(fixed_shape)
            if d.export_filename:
                self.export(d.export_filename, d.export_type)
        self.shape = fixed_shape

    def update_mesh(self, shape: TopoDS_Shape):
        self.clear_cache()
        d = self.declaration
        gen = self.gen
        mesh = self.mesh
        mesh_vs = self.ais_shape
        mesh.ShapeToMesh(shape)
        d.prepare_mesh(self.gen, self.mesh, shape)

        with log_time("Computing mesh..."):
            result = gen.Compute(mesh, mesh.GetShapeToMesh())
            if not result:
                raise RuntimeError(f"Failed to mesh {d}: {result}")

        vs_link = self.vs_link = SMESH_MeshVSLink(mesh)
        mesh_vs.SetDataSource(vs_link)
        self.smesh_ds = mesh.GetMeshDS()

        self.builder = MeshVS_MeshPrsBuilder(mesh_vs)
        self.node_builder = MeshVS_NodalColorPrsBuilder(mesh_vs, 3 | 8, vs_link, 1)
        self.element_builder = MeshVS_ElementalColorPrsBuilder(
            mesh_vs, 3 | 10, vs_link, 2
        )

        with log_time("Processing mesh..."):
            d.process_mesh()

        self.update_style()

        with log_time("Colorizing mesh..."):
            d.colorize_mesh()

        mesh_vs.AddBuilder(self.builder, True)
        mesh_vs.AddBuilder(self.node_builder)
        mesh_vs.AddBuilder(self.element_builder)
        mesh_vs.SetDisplayMode(2)  # Shaded
        mesh_vs.UpdateSelectableNodes()
        # mesh_vs.SetMeshSelMethod(30)

    def update_style(self):
        """Update mesh colors."""
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

    def clear_cache(self):
        """Free up cached elements"""
        self.nodes = {}
        self.elements = {}
        self.faces = {}
        self.volumes = {}

    def destroy(self):
        """Cleanup resources"""
        super().destroy()
        self.clear_cache()

        if self.vs_link:
            del self.vs_link
        if self.smesh_ds:
            del self.smesh_ds
        if self.ais_shape:
            del self.ais_shape
        if self.gen:
            del self.gen
        if self.builder:
            del self.builder
        if self.node_builder:
            del self.node_builder
        if self.element_builder:
            del self.element_builder

    def export(self, filename: str, export_type: str, *args):
        """Export the mesh. The extension is added automatically

        Parameters
        ----------
        filename: String
            The base filename (excluding the extension)
        export_type: String
            The export type. Must map to one of the Export functions

        """
        filename = os.path.abspath(filename)
        filename = f"{filename}.{export_type.lower()}"
        log.info(f"Exporting mesh to '{filename}'")
        export = getattr(self.mesh, f"Export{export_type.upper()}")
        if export_type == "stl" and not args:
            args = [True]  # Use ascii
        export(filename, *args)
        log.info("Ok!")

    def _lookup_element(
        self, key: Union[int, SMDS_MeshElement], cache: dict
    ) -> Element:
        """Get or create a cached element"""
        id = key.GetID() if isinstance(key, SMDS_MeshElement) else key
        element = cache.get(id)
        if element is None:
            if isinstance(key, SMDS_MeshElement):
                item = key
            else:
                item = self.vs_link.FindElement(id)
                if item is None:
                    raise KeyError(id)
            element = cache[id] = create_element(id, self, item)
        return element

    # ------------------------------------------------------------------------
    # Proxy API
    # ------------------------------------------------------------------------
    def find_node(self, key: Union[int, SMDS_MeshNode]) -> Node:
        """Find the Node with the given ID."""
        id = key.GetID() if isinstance(key, SMDS_MeshNode) else key
        node = self.nodes.get(id)
        if node is None:
            if isinstance(key, SMDS_MeshNode):
                item = key
            else:
                item = self.vs_link.FindNode(id)
                if item is None:
                    raise KeyError(id)
            node = self.nodes[id] = create_node(id, self, item)
        return node

    def find_element(self, key: Union[int, SMDS_MeshElement]) -> Element:
        """Find the Element with the given ID."""
        return self._lookup_element(key, self.elements)

    def find_face(self, key: Union[int, SMDS_MeshElement]) -> Element:
        """Find the Face with the given ID."""
        return self._lookup_element(key, self.faces)

    def find_volume(self, key: Union[int, SMDS_MeshElement]) -> Element:
        """Find the Volume with the given ID."""
        return self._lookup_element(key, self.volumes)

    def set_source(self, source):
        self.update_shape()

    def set_algorithm(self, algo):
        self.update_shape()

    def set_node_color(self, index: int, color: Color):
        c, _ = color_to_quantity_color(color)
        self.node_builder.SetColor(index, c)

    def set_element_color(
        self, index: int, front_color: Color, back_color: Optional[Color] = None
    ):
        front, _ = color_to_quantity_color(front_color)
        if back_color is None:
            self.element_builder.SetColor1(index, front)
        else:
            back, _ = color_to_quantity_color(back_color)
            self.element_builder.SetColor2(index, front, back)
