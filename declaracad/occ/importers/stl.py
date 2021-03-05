"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
from OCCT.BRep import BRep_Builder
from OCCT.RWStl import RWStl
from OCCT.TopoDS import TopoDS_Face
from declaracad.occ.api import TopoShape


def load_stl(filename):
    """ Load a stl model """
    builder = BRep_Builder()
    shape = TopoDS_Face()
    builder.MakeFace(shape)
    poly = RWStl.ReadFile_(filename)
    builder.UpdateFace(shape, poly)
    return [TopoShape(shape=shape)]
