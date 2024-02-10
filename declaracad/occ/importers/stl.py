"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
from math import pi

from OCCT.BRep import BRep_Builder
from OCCT.Poly import Poly_Connect, Poly_PolygonOnTriangulation
from OCCT.RWStl import RWStl
from OCCT.TColStd import TColStd_Array1OfInteger
from OCCT.TopoDS import (
    TopoDS_Compound,
    TopoDS_Edge,
    TopoDS_Face,
    TopoDS_Shell,
    TopoDS_Solid,
    TopoDS_Vertex,
    TopoDS_Wire,
)

from declaracad.occ.api import TopoShape


def load_stl(
    filename: str,
    merge_angle: float = pi / 360,
    create_vertices: bool = False,
    create_edges: bool = False,
    tol: float = 1e-6,
) -> list[TopoShape]:
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
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    poly = RWStl.ReadFile_(filename, merge_angle)
    face = TopoDS_Face()
    builder.MakeFace(face)
    builder.UpdateFace(face, poly)
    if create_edges:
        pass
    #         pc = Poly_Connect(poly)
    # #         num_free = 0
    # #         n = poly.NbTriangles()
    # #         for i in range(1, n):
    # #             out = pc.Triangles(i)
    # #             if out[0] == 0:
    # #                 num_free += 1
    # #             if out[1] == 0:
    # #                 num_free += 1
    # #             if out[2] == 0:
    # #                 num_free += 1
    # #
    # #         nodes = TColStd_Array1OfInteger(1, max(1, 2*num_free))
    #
    #         for i in range(1, poly.NbTriangles()):
    #             #print(f"{i} of {n}")
    #             out = pc.Triangles(i)
    #             for j in range(3):
    #                 if out[j] == 0:
    #                     t = poly.Triangle(i)
    #                     pts = TColStd_Array1OfInteger(1, 3)
    #                     pts.SetValue(1, t.Value(1))
    #                     pts.SetValue(2, t.Value(2))
    #                     pts.SetValue(3, t.Value(3))
    #                     p = Poly_PolygonOnTriangulation(pts)
    #                     edge = TopoDS_Edge()
    #                     builder.MakeEdge(edge, p, poly)
    #                     wire = TopoDS_Wire()
    #                     builder.MakeWire(wire)
    #                     builder.Add(wire, edge)
    #                     builder.Add(face, wire)
    #             #builder.Add(compound, edge)
    # builder.UpdateEdge(edge, edge)
    elif create_vertices:
        for i in range(1, poly.NbNodes()):
            vertex = TopoDS_Vertex()
            builder.MakeVertex(vertex, poly.Node(i), tol)
            builder.Add(face, vertex)

    shell = TopoDS_Shell()
    builder.MakeShell(shell)
    builder.Add(shell, face)
    solid = TopoDS_Solid()
    builder.MakeSolid(solid)
    builder.Add(solid, shell)
    builder.Add(compound, solid)
    # builder.Add(compound, vertex)
    return [TopoShape(shape=compound)]
