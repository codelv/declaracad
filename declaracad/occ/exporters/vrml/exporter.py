"""
Copyright (c) 2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 10, 2018

@author: jrm
"""
import os
import enaml
from textwrap import dedent
from atom.api import Constant, Enum, Float, Str
from declaracad.occ.api import load_model
from declaracad.viewer.plugin import ModelExporter

from OCCT.VrmlAPI import VrmlAPI_Writer, VrmlAPI_RepresentationOfShape


class VrmlExporter(ModelExporter):
    extension = 'vrml'
    deflection = Float(-1, strict=False).tag(help=dedent("""
        The default value is -1. When the deflection value is less than 0,
        the deflection is calculated from the relative size of the shape.
        """.strip()))
    version = Enum(2, 1)
    representation = Enum(
        'both',
        'shaded',
        'wire-frame'
    )

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm
            return OptionsForm

    def export(self):
        """ Export a DeclaraCAD model from an enaml file to VRML based on the
        given options.

        Parameters
        ----------
        options: declaracad.occ.plugin.ExportOptions

        """
        # Set all params
        exporter = VrmlAPI_Writer()
        exporter.SetDeflection(self.deflection)

        rep_name = self.representation.title().replace('-', '')
        exporter.SetRepresentation(
            getattr(VrmlAPI_RepresentationOfShape,
                    f'VrmlAPI_{rep_name}Representation'))
        v = self.version
        output_path = self.path

        # Load the enaml model file
        parts = load_model(self.filename)

        # Remove old file
        if os.path.exists(output_path):
            os.remove(output_path)

        for part in parts:
            # Render the part from the declaration
            s = part.render()

            # Transfer all shapes
            if not exporter.Write(s, output_path, v):
                raise RuntimeError("Failed to write shape")
        print(f"Written to {output_path}")

