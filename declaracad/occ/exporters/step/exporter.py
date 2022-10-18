"""
Copyright (c) 2018-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 10, 2018

@author: jrm
"""
import os

import enaml
from atom.api import Enum, Float, Str
from OCCT.HeaderSection import HeaderSection_FileDescription, HeaderSection_FileName
from OCCT.IFSelect import IFSelect_RetDone
from OCCT.Interface import Interface_Static
from OCCT.STEPCAFControl import STEPCAFControl_Writer
from OCCT.TCollection import TCollection_HAsciiString

from declaracad.occ.api import Shape
from declaracad.occ.impl.document import create_hascii_list, create_xcaf_document
from declaracad.viewer.plugin import ModelExporter

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

    # Step header fields
    name = Str().tag(help="Step header file name")
    author = Str().tag(help="Step header author(s). If multiple seperate with a comma.")
    description = Str().tag(help="Step header description")
    company = Str().tag(
        help="Step header company name. If multiple seperate with a comma."
    )
    authorization = Str().tag(help="Step authorization header / license")

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm

            return OptionsForm

    def export(self, shapes: list[Shape]):
        """Export a DeclaraCAD model to a STEP file based on the given options."""
        # Set all params
        doc = create_xcaf_document(shapes)

        # Send it
        exporter = STEPCAFControl_Writer()
        exporter.SetNameMode(True)
        exporter.SetColorMode(True)
        step_model = exporter.Writer().WS().Model()

        if self.description:
            tp = HeaderSection_FileDescription.get_type_descriptor_()
            entity = step_model.HeaderEntity(tp)
            entity.SetDescription(create_hascii_list(self.description.split("\n")))

        tp = HeaderSection_FileName.get_type_descriptor_()
        entity = step_model.HeaderEntity(tp)
        entity.SetOriginatingSystem(TCollection_HAsciiString("DeclaraCAD"))

        if self.author:
            names = [v.strip() for v in self.author.split(",")]
            entity.SetAuthor(create_hascii_list(names))

        if self.name:
            entity.SetName(TCollection_HAsciiString(self.name))

        if self.company:
            names = [v.strip() for v in self.company.split(",")]
            entity.SetOrganization(create_hascii_list(names))

        if self.authorization:
            # Typo!
            entity.SetAuthorisation(TCollection_HAsciiString(self.authorization))

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
