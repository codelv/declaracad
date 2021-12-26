"""
Copyright (c) 2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 10, 2018

@author: jrm
"""
import os
import enaml
from atom.api import Constant, Enum, Float, Str
from declaracad.occ.api import Part, load_model
from declaracad.viewer.plugin import ModelExporter
from declaracad.occ.impl.utils import color_to_quantity_color

from OCCT.BinXCAFDrivers import BinXCAFDrivers
from OCCT.STEPCAFControl import STEPCAFControl_Writer
from OCCT.XCAFApp import XCAFApp_Application
from OCCT.Interface import Interface_Static
from OCCT.IFSelect import IFSelect_RetDone
from OCCT.TCollection import TCollection_ExtendedString
from OCCT.TDocStd import TDocStd_Document
from OCCT.TDataStd import TDataStd_Name
from OCCT.XCAFDoc import (
    XCAFDoc_DocumentTool,
    XCAFDoc_Material,
    XCAFDoc_Color,
    XCAFDoc_ColorGen,
)
from OCCT.XmlXCAFDrivers import XmlXCAFDrivers
from OCCT.Quantity import Quantity_Color


SetCVal = Interface_Static.SetCVal_
SetIVal = Interface_Static.SetIVal_
SetRVal = Interface_Static.SetRVal_

VERTEX_MODES = {"one compound": 0, "single vertex": 1}
PRECISION_MODES = {"least": -1, "average": 0, "greatest": 1, "session": 2}
ASSEMBLY_MODES = {"off": 0, "on": 1, "auto": 2}
SURFACECURVE_MODES = {"off": 0, "on": 1}


class StepExporter(ModelExporter):
    """
    References
    ----------
    1. https://dev.opencascade.org/doc/overview/html/
        occt_user_guides__step.html#occt_step_3
    2. https://github.com/trelau/AFEM

    """

    extension = "step"
    schema = Enum("AP214 CD", "AP214 DIS", "AP203", "AP214 IS", "AP242 DIS")
    units = Enum("mm", "in")
    precision_mode = Enum("average", "least", "greatest", "session")
    precision_val = Float(0.0001).tag(
        help="This parameter gives the uncertainty for STEP entities "
        "constructed from OCCT shapes when the write.precision.mode "
        "parameter value is 'greatest'."
    )
    product_name = Str().tag(
        help="Defines the text string that will be used for field `name' of "
        "PRODUCT entities written to the STEP file."
    )
    assembly_mode = Enum("off", "on", "auto")
    surfacecurve_mode = Enum("on", "off")
    vertex_mode = Enum("one compound", "single vertex")

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm

            return OptionsForm

    def export(self):
        """Export a DeclaraCAD model from an enaml file to an STL based on the
        given options.

        Parameters
        ----------
        options: declaracad.occ.plugin.ExportOptions

        """
        # Set all params
        app = XCAFApp_Application.GetApplication_()
        fmt = TCollection_ExtendedString("BinXCAF")
        doc = TDocStd_Document(fmt)
        app.InitDocument(doc)

        shape_tool = XCAFDoc_DocumentTool.ShapeTool_(doc.Main())
        color_tool = XCAFDoc_DocumentTool.ColorTool_(doc.Main())
        material_tool = XCAFDoc_DocumentTool.MaterialTool_(doc.Main())
        notes_tool = XCAFDoc_DocumentTool.NotesTool_(doc.Main())

        # Load the enaml model file
        parts = load_model(self.filename)

        for part in parts:
            # Render the part from the declaration
            part.render()
            for s in part.proxy.walk_shapes():
                d = s.declaration
                ais_shape = s.ais_shape
                is_part = isinstance(d, Part)

                label = s.tdf_label = shape_tool.NewShape()
                shape = ais_shape.Shape().Located(s.location)
                shape_tool.SetShape(label, shape)

                if d.color:
                    color, alpha = color_to_quantity_color(d.color)
                    color_tool.SetColor(shape, color, XCAFDoc_ColorGen)
                # if d.material:
                #    XCAFDoc_Material.Set_(label, ais_shape.Material())
                name = TCollection_ExtendedString(
                    d.name or d.description or d.__class__.__name__
                )
                TDataStd_Name.Set_(label, name)

        # Send it
        exporter = STEPCAFControl_Writer()
        exporter.SetNameMode(True)
        exporter.SetColorMode(True)
        SetIVal("write.precision.mode", PRECISION_MODES[self.precision_mode])
        if self.precision_mode == "greatest":
            SetRVal("write.precision.val", self.precision_val)
        SetIVal("write.step.assembly", ASSEMBLY_MODES[self.assembly_mode])
        SetCVal("write.step.schema", self.schema)
        if self.product_name:
            SetCVal("write.step.product.name", self.product_name)
        SetIVal("write.surfacecurve.mode", SURFACECURVE_MODES[self.surfacecurve_mode])
        SetCVal("write.step.unit", self.units.upper())
        SetIVal("write.step.vertex.mode", VERTEX_MODES[self.vertex_mode])
        exporter.Transfer(doc)
        status = exporter.Write(self.path)
        if status != IFSelect_RetDone or not os.path.exists(self.path):
            raise RuntimeError("Failed to write shape")
