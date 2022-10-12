"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
from OCCT.BRep import BRep_Builder
from OCCT.BRepTools import BRepTools
from OCCT.TopoDS import TopoDS_Shape

from declaracad.occ.api import Shape, TopoShape


def load_brep(filename: str, **options) -> list[Shape]:
    """Load a brep model"""
    shape = TopoDS_Shape()
    builder = BRep_Builder()
    BRepTools.Read_(shape, filename, builder, None)
    # TODO: Load colors
    return [TopoShape(shape=shape)]
