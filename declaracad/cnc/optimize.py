"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 22, 2020

@author: jrm
"""
import sys
import time
from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from declaracad.occ.api import Topology
from declaracad.occ.geom import coerce_point
from declaracad.core.utils import log
from . import interpolate


def optimize_graph(wires, optimizer_timeout=30):
    """Try to reduce the number of head lifts by retracing common paths.

    Parameters
    ----------
    wires: List[TopoDS_Wire]
        Unordered set of wires
    Returns
    -------
    wires: List[TopoDS_Wires]
        Wires in the optimal move order

    """
    if len(wires) < 2:
        return wires

    graph = interpolate.build_edge_graph(wires)
    standalone = []
    # for vertex, edges in graph.items():
    #    if len(edges)

    return standalone


def optimize_moves(wires, start_point, reverse=False, optimizer_timeout=30):
    """Use Dijkstra's algorithm to find the shortest path between
    a set of wires. Ported from Inkcut

    Parameters
    ----------
    wires: List[TopoDS_Wire]
        Unordered set of wires
    start_point: Point
        Starting point
    reverse: Bool
        Revers the point order
    Returns
    -------
    wires: List[TopoDS_Wires]
        Wires in the optimal move order

    """
    if len(wires) < 2:
        return wires
    now = time.time()
    time_limit = now + optimizer_timeout

    original = wires[:]
    subpaths = [BRepAdaptor_CompCurve(w) for w in wires]
    result = []
    sp = subpaths[0]
    p = start_point.proxy
    while subpaths:
        best = sys.maxsize
        shortest = None
        for sp in subpaths:
            t = sp.LastParameter() if reverse else sp.FirstParameter()
            start_point = sp.Value(t)
            d = p.Distance(start_point)
            if d < best:
                best = d
                shortest = sp

        t = shortest.FirstParameter() if reverse else shortest.LastParameter()
        p = shortest.Value(t)
        result.append(shortest)
        subpaths.remove(shortest)

        # time.time() is slow so limit the calls
        if time.time() > time_limit:
            result.extend(subpaths)  # At least part of it is optimized
            log.warning("Shortest path search aborted (time limit reached)")
            break

    return [sp.Wire() for sp in result]


def optimize_points(points, start_point, optimizer_timeout=30):
    """Use Dijkstra's algorithm to find the shortest path between
    a set of points. Ported from Inkcut

    Parameters
    ----------
    points: List[Point]
        Unordered set of wires
    start_point: Point
        Starting point

    Returns
    -------
    points: List[Point]
        Points in the optimal move order

    """
    if len(points) < 2:
        return points
    now = time.time()
    time_limit = now + optimizer_timeout

    remaining = [coerce_point(p) for p in points]
    result = []
    p = coerce_point(start_point)
    while remaining:
        best = sys.maxsize
        closest = None
        for pt in remaining:
            d = p.distance(pt)
            if d < best:
                best = d
                closest = pt

        p = closest
        result.append(closest)
        remaining.remove(closest)

        # time.time() is slow so limit the calls
        if time.time() > time_limit:
            result.extend(remaining)  # At least part of it is optimized
            log.warning("Shortest path search aborted (time limit reached)")
            break

    return result
