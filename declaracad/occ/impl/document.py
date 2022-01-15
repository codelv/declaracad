"""
Copyright (c) 2018-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from declaracad.occ.api import Part, load_model
from declaracad.occ.impl.utils import color_to_quantity_color

from OCCT.Interface import Interface_HArray1OfHAsciiString
from OCCT.TCollection import TCollection_ExtendedString, TCollection_HAsciiString
from OCCT.TDataStd import TDataStd_Name
from OCCT.TDocStd import TDocStd_Document
from OCCT.XCAFApp import XCAFApp_Application
from OCCT.XCAFDoc import (
    XCAFDoc_DocumentTool,
    XCAFDoc_Material,
    XCAFDoc_Color,
    XCAFDoc_ColorGen,
)



def create_xcaf_document(filename: str) -> TDocStd_Document:
    """ Load the model and create an XCAF document for it.

    Parameters
    ----------
    filename: str
        The path to the file

    Returns
    -------
    doc: TDocStd_Document
        The XCAF document

    """
    app = XCAFApp_Application.GetApplication_()
    fmt = TCollection_ExtendedString("BinXCAF")
    doc = TDocStd_Document(fmt)
    app.InitDocument(doc)

    shape_tool = XCAFDoc_DocumentTool.ShapeTool_(doc.Main())
    color_tool = XCAFDoc_DocumentTool.ColorTool_(doc.Main())
    material_tool = XCAFDoc_DocumentTool.MaterialTool_(doc.Main())
    notes_tool = XCAFDoc_DocumentTool.NotesTool_(doc.Main())

    # Load the enaml model file
    parts = load_model(filename)

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
    return doc



def create_hascii_list(values):
    r = Interface_HArray1OfHAsciiString(1, len(values))
    for i, v in enumerate(values):
        r.SetValue(i + 1, TCollection_HAsciiString(v))
    return r
