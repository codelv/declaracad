"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""

from OCCT.IFSelect import IFSelect_ItemsByEntity, IFSelect_RetDone
from OCCT.STEPControl import STEPControl_Reader

from declaracad.occ.api import TopoShape


def load_step(filename: str) -> list[TopoShape]:
    """Load a stp model"""
    reader = STEPControl_Reader()
    status = reader.ReadFile(filename)
    if status != IFSelect_RetDone:
        raise ValueError("Failed to load: {}".format(filename))
    reader.PrintCheckLoad(False, IFSelect_ItemsByEntity)
    reader.PrintCheckTransfer(False, IFSelect_ItemsByEntity)
    ok = reader.TransferRoot()
    if not ok:
        raise ValueError("Failed to load: {}".format(filename))
    return [TopoShape(shape=reader.Shape(1))]
