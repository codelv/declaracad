"""
Copyright (c) 2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 10, 2018

@author: jrm
"""

import os

import enaml
from atom.api import Bool, Float
from OCCT.BRep import BRep_Builder
from OCCT.BRepMesh import BRepMesh_IncrementalMesh
from OCCT.StlAPI import StlAPI_Writer
from OCCT.TopoDS import TopoDS_Compound

from declaracad.occ.api import Shape
from declaracad.viewer.plugin import ModelExporter


class StlExporter(ModelExporter):
    extension = "stl"
    linear_deflection = Float(0.05, strict=False)
    angular_deflection = Float(0.5, strict=False)
    relative = Bool()
    binary = Bool()

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm

            return OptionsForm

    def export(self, shapes: list[Shape]):
        """Export a DeclaraCAD model from an enaml file to an STL based on the
        given options.

        Parameters
        ----------
        options: declaracad.occ.plugin.ExportOptions

        """

        # Make a compound of compounds (if needed)
        compound = TopoDS_Compound()
        builder = BRep_Builder()
        builder.MakeCompound(compound)

        for part in shapes:
            # Render the part from the declaration
            shape = part.render()

            # Must mesh the shape firsts
            if hasattr(shape, "Shape"):
                builder.Add(compound, shape.Shape())
            else:
                builder.Add(compound, shape)

        #: Build the mesh
        exporter = StlAPI_Writer()
        # TODO: pyOCCT needs to support updating the reference
        # exporter.SetASCIIMode(not self.binary)
        mesh = BRepMesh_IncrementalMesh(
            compound,
            self.linear_deflection,
            self.relative,
            self.angular_deflection,
            True,
        )
        mesh.Perform()
        if not mesh.IsDone():
            raise RuntimeError("Failed to create the mesh")

        exporter.Write(compound, self.path)

        if not os.path.exists(self.path):
            raise RuntimeError("Failed to write shape")
