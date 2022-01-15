"""
Copyright (c) 202, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import enaml
from atom.api import Bool, Enum, Float, Str
from declaracad.occ.api import Part, load_model
from declaracad.viewer.plugin import ModelExporter
from declaracad.occ.impl.document import (
    create_xcaf_document, create_hascii_list
)

from OCCT.Interface import Interface_Static
from OCCT.IFSelect import IFSelect_RetDone
from OCCT.IGESCAFControl import IGESCAFControl_Writer


SetCVal = Interface_Static.SetCVal_
SetIVal = Interface_Static.SetIVal_
SetRVal = Interface_Static.SetRVal_


class IgesExporter(ModelExporter):
    """

    References
    ----------
    1. https://dev.opencascade.org/doc/overview/html/
       occt_user_guides__iges.html

    """

    extension = "igs"

    convertsurface_mode = Bool(False).tag(
        help="Convert elementary surfaces to IGES entities")
    brep_mode = Enum("faces", "brep").tag(
        help="If 'faces', faces will be translated to IGES 144 (Trimmed sruface) entities, "
             "no BRep entites will be written to the IGES file. If set to 'brep', "
             "faces will be translated to IGES 510 (Face) entities, the IGES fill will "
             "contain BRep entites"
    )
    units = Enum("mm", "inch")
    precision_mode = Enum("average", "least", "greatest", "session")
    precision_val = Float(0.0001).tag(
        help="This parameter gives the uncertainty for IGES entities "
        "constructed from OCCT shapes when the precision mode "
        "parameter value is 'greatest'."
    )

    # Step header fields
    author = Str().tag(help="Model author(s). If multiple seperate with a comma.")
    company = Str().tag(help='Model header company name. If multiple seperate with a comma.')

    @classmethod
    def get_options_view(cls):
        with enaml.imports():
            from .options import OptionsForm

            return OptionsForm

    def export(self):
        """Export a DeclaraCAD model to an IGES file based on the given options.

        """
        # Set all params
        doc = create_xcaf_document(self.filename)

        # Send it
        exporter = IGESCAFControl_Writer()
        exporter.SetNameMode(True)
        exporter.SetColorMode(True)

        SetCVal("write.iges.header.author", self.author)
        SetCVal("write.iges.header.company", self.company)
        SetCVal("write.iges.header.product", "DeclaraCAD")

        precision_mode = IgesExporter.precision_mode.items.index(self.precision_mode)-1
        SetIVal("write.precision.mode", precision_mode)
        if self.precision_mode == "greatest":
            SetRVal("write.precision.val", self.precision_val)
        brep_mode = IgesExporter.brep_mode.items.index(self.brep_mode)
        SetIVal("write.iges.brep.mode", brep_mode)
        SetRVal("write.convertsurface.mode", self.convertsurface_mode)
        SetCVal("write.iges.unit", self.units.upper())
        exporter.Transfer(doc)
        status = exporter.Write(self.path)
        if status != IFSelect_RetDone or not os.path.exists(self.path):
            raise RuntimeError("Failed to write shape")
