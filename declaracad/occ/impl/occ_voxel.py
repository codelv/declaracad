"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on July 22, 2022

@author: jrm
"""
from atom.api import ForwardTyped, Typed
from enaml.colors import parse_color
from OCCT.BRepAlgoAPI import BRepAlgoAPI_Common
from OCCT.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCCT.Voxel import (
    Voxel_BoolDS,
    Voxel_ColorDS,
    Voxel_DS,
    Voxel_FastConverter,
    Voxel_Prs,
    Voxel_ROctBoolDS,
    Voxel_VDM_BOXES,
    Voxel_VDM_NEARESTBOXES,
    Voxel_VDM_NEARESTPOINTS,
    Voxel_VDM_POINTS,
)

from declaracad.extensions import VoxelClient_PrsGl
from declaracad.occ.voxel import ProxyVoxel, ProxyVoxelTopology

from .occ_shape import OccDependentShape, Shape, coerce_axis
from .utils import color_to_quantity_color


class OccVoxelTopology(ProxyVoxelTopology):
    voxel = ForwardTyped(lambda: OccVoxel)


class OccVoxel(OccDependentShape, ProxyVoxel):
    topology = Typed(OccVoxelTopology)
    converter = Typed(Voxel_FastConverter)
    voxel = Typed(Voxel_DS)
    ais_shape = Typed(VoxelClient_PrsGl)

    def _default_ais_shape(self):
        d = self.declaration
        prs = VoxelClient_PrsGl()
        prs.SetDisplayMode(Voxel_VDM_POINTS)
        prs.SetPointSize(3)
        color = d.color or parse_color("blue")
        c, a = color_to_quantity_color(color)
        prs.SetColor(c)
        if a:
            prs.SetTransparency(0)
        prs.SetQuadrangleSize(10)
        voxel = self.voxel
        if isinstance(voxel, Voxel_ROctBoolDS):
            prs.SetROctBoolVoxels(voxel)
        elif isinstance(voxel, Voxel_BoolDS):
            prs.SetBoolVoxels(voxel)
        elif isinstance(voxel, Voxel_ColorDS):
            prs.SetColorVoxels(voxel)
        else:
            raise TypeError(f"Voxel '{voxel}' is invalid")
        # prs.SetDegenerateMode(True)
        # prs.SetUsageOfGLlists(True)
        return prs

    def _default_topology(self):
        if self.ais_shape is None:
            self.declaration.render()  # Force build the shape
        return OccVoxelTopology(voxel=self)

    def update_shape(self, change=None):
        if self.voxel:
            return  # Already created
        d = self.declaration
        shape = d.source
        if shape:
            if isinstance(shape, Shape):
                shape = shape.proxy.shape
        else:
            child = self.get_first_child()
            if child is not None:
                shape = child.shape
        start, end = d.bounds
        nx, ny, nz = d.splits

        if d.mode == "octree":
            Voxel = Voxel_ROctBoolDS
        elif d.mode == "bool":
            Voxel = Voxel_BoolDS
        elif d.mode == "color":
            Voxel = Voxel_ColorDS
        else:
            raise ValueError("Unknown voxel type")

        voxel = Voxel(start.x, start.y, start.z, end.x, end.y, end.z, nx, ny, nz)

        if shape is None:
            shape = BRepPrimAPI_MakeBox(start.proxy, end.proxy).Shape()
        elif d.fill:
            # Must clip or fill does not work
            bbox = BRepPrimAPI_MakeBox(start.proxy, end.proxy).Shape()
            shape = BRepAlgoAPI_Common(bbox, shape).Shape()

        self.converter = converter = Voxel_FastConverter(
            shape, voxel, d.deflection, nx, ny, nz, d.threads
        )

        if not converter.Convert(0, d.threads) or not converter.FillInVolume(
            d.fill, d.threads
        ):
            # if not converter.ConvertUsingSAT(0, d.threads):
            raise RuntimeError("Failed to convert to voxels")
        if isinstance(voxel, Voxel_ROctBoolDS):
            voxel.OptimizeMemory()
        self.voxel = voxel
        self.shape = shape

    def cleanup(self):
        if self.converter:
            del self.converter
        if self.voxel:
            del self.voxel

    def destroy(self):
        super().destroy()
        self.cleanup()

    def set_source(self, source):
        self.cleanup()
        self.update_shape()

    def set_deflection(self, deflection: float):
        self.cleanup()
        self.update_shape()

    def set_domain(self, domain: tuple):
        self.cleanup()
        self.update_shape()

    def set_splits(self, splits: tuple):
        self.cleanup()
        self.update_shape()

    def set_threads(self, threads: int):
        self.cleanup()
        self.update_shape()

    def set_mode(self, mode: str):
        self.cleanup()
        self.update_shape()
