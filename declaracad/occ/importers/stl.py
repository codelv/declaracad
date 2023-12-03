"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
from math import pi
from OCCT.BRep import BRep_Builder
from OCCT.RWStl import RWStl
from OCCT.TopoDS import TopoDS_Face

from declaracad.occ.api import TopoShape


def load_stl(filename: str, merge_angle: float = pi/360) -> list[TopoShape]:
    """Load a stl model

    Parameters
    ----------
    filename: str
        Path to stl file
    merge_angle: float
        maximum angle in radians between triangles to merge equal nodes

    Returns
    -------
    result: list[TopoDS_Shape]
        Loaded shape
    """
    builder = BRep_Builder()
    shape = TopoDS_Face()
    builder.MakeFace(shape)
    poly = RWStl.ReadFile_(filename, merge_angle)
    builder.UpdateFace(shape, poly)
    return [TopoShape(shape=shape)]
