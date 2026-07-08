"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 22, 2020

@author: jrm
"""

import sys
import time
from typing import Any, Callable, Optional

from OCCT.BRepAdaptor import BRepAdaptor_CompCurve
from OCCT.TopoDS import TopoDS_Wire

from declaracad.core.utils import log
from declaracad.occ.geom import Point, coerce_point


def optimize_moves(
    wires: list[TopoDS_Wire],
    start_point: Point,
    reverse: bool = False,
    optimizer_timeout: float = 120,
    enabled: bool = True,
) -> list[TopoDS_Wire]:
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
    enabled: Bool
        If False, disable optimization
    Returns
    -------
    wires: List[TopoDS_Wires]
        Wires in the optimal move order

    """
    if len(wires) < 2 or not enabled:
        return wires
    now = time.time()
    time_limit = now + optimizer_timeout

    subpaths: list[BRepAdaptor_CompCurve] = [BRepAdaptor_CompCurve(w) for w in wires]
    result: list[BRepAdaptor_CompCurve] = []
    sp = subpaths[0]
    p = start_point.proxy
    while subpaths:
        best = sys.maxsize
        shortest: Optional[BRepAdaptor_CompCurve] = None
        for sp in subpaths:
            t = sp.LastParameter() if reverse else sp.FirstParameter()
            start_point = sp.Value(t)
            d = p.Distance(start_point)
            if shortest is None or d < best:
                best = d
                shortest = sp
        assert shortest is not None, f"Shortest of {subpaths} is invalid"
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


def optimize_points(
    points: list[Point],
    start_point: Point,
    optimizer_timeout: float = 120,
    enabled: bool = True,
) -> list[Point]:
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
    if len(points) < 2 or not enabled:
        return points
    now = time.time()
    time_limit = now + optimizer_timeout

    remaining = [coerce_point(p) for p in points]
    result: list[Point] = []
    p = coerce_point(start_point)
    while remaining:
        best: float = sys.maxsize
        closest: Optional[Point] = None
        for pt in remaining:
            d = p.distance(pt)
            if d < best:
                best = d
                closest = pt
        assert closest is not None
        p = closest
        result.append(closest)
        remaining.remove(closest)

        # time.time() is slow so limit the calls
        if time.time() > time_limit:
            result.extend(remaining)  # At least part of it is optimized
            log.warning("Shortest path search aborted (time limit reached)")
            break

    return result


def optimize_order(
    data: list, start_point: Point, key: Callable[[Any], Point], **kwargs
) -> list:
    """Reorder a generic list of operations based on the start point and
    list of operation start points.

    Parameters
    ----------
    data: list
        The list of data to re-order
    start_point: Point
        The starting point
    key: Callable -> Point
        A callable which takes an entry from the data nad must return the
        start point of the operation

    Returns
    -------
    reordered_data: list
        The re-orderd list

    """
    if len(data) <= 1:
        return data
    data_points: list[Point] = [key(it) for it in data]
    reordered_data = []
    for pt in optimize_points(data_points, start_point, **kwargs):
        i = data_points.index(pt)
        reordered_data.append(data[i])
    return reordered_data
