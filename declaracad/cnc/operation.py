"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Nov 9, 2021

@author: jrm
"""
import math
import traceback
from math import ceil, sqrt, sin, cos
from typing import List as ListType
from atom.api import Atom, Bool, Enum, Float, Instance, Str, Coerced
from datetime import datetime
from declaracad.occ.geom import coerce_point
from declaracad.occ.api import (
    DisplayArrow, Direction, Point, Part, Polyline, Topology, Vertex, Wire, Arc,
    HalfSpace, Cylinder, Timer, Looper, Include, Conditional, Offset
)
from declaracad.cnc.optimize import optimize_points
from declaracad.cnc.interpolate import group_connected_faces
from declaracad.cnc.cutters import Tool
from enaml.core.declarative import d_, d_func



def generate_arc_gcode(
    arc: Arc,
    format_value,
    incremental: bool = True
) -> ListType[str]:
    """ Generate gcodee for an Arc """

    cmds = []
    d = arc.direction
    center = arc.position
    start, end = arc.points
    delta = center - start if incremental else center
    x, y, z = map(format_value, end)
    if d == (0, 0, 1) or d == (0, 0, -1):
        axis = 2
        if arc.clockwise:
            code = 'G3' if d[axis] == -1 else 'G2'
        else:
            code = 'G3' if d[axis] == 1 else 'G2'
        # XY plane
        i, j = format_value(delta.x), format_value(delta.y)
        cmds.append(f'{code} X{x} Y{y} Z{z} I{i} J{j}')
    elif d == (0, 1, 0) or d == (0, -1, 0):
        axis = 1
        if arc.clockwise:
            code = 'G3' if d[axis] == -1 else 'G2'
        else:
            code = 'G3' if d[axis] == 1 else 'G2'
        # XZ plane
        i, k = format_value(delta.x), format_value(delta.z)
        cmds.append("G18 (XZ-plane)")
        cmds.append(f'{code} X{x} Z{z} Y{y} I{i} K{k}')
        cmds.append('G17 (XY-plane)') # Restore G17
    elif d == (1, 0, 0) or d == (-1, 0, 0):
        axis = 0
        if arc.clockwise:
            code = 'G3' if d[axis] == -1 else 'G2'
        else:
            code = 'G3' if d[axis] == 1 else 'G2'

        # YZ plane
        j, k = format_value(delta.y), format_value(delta.z)
        cmds.append("G19 (YZ-plane)")
        cmds.append(f'{code} Y{y} Z{z} X{x} J{j} K{k}')
        cmds.append('G17 (XY-plane)') # Restore G17
    else:
        raise NotImplementedError(f"Arc direction {d} cannot be converted")

    if not arc.description:
        arc.description = "Gcode: \n%s\n" % '\n'.join(cmds)

    return cmds

def generate_polyline_gcode(
    polyline: Polyline,
    format_value,
    rapid: bool = False
) -> ListType[str]:
    """ Generate gcodee for a Polyline """
    cmds = []
    code = 'G0' if rapid else 'G1'
    for p in polyline.points:
        x, y, z = map(format_value, p)
        cmds.append(f'{code} X{x} Y{y} Z{z}')
    return cmds


def generate_wire_gcode(wire: Wire, format_value) -> ListType[str]:
    """ Generate code for a Wire """
    cmds = []
    for edge in wire.topology.edges:
        topo = Topology(shape=edge)
        if Topology.is_line(edge):
            for p in (topo.start_point, topo.end_point):
                x, y, z = map(format_value, p)
                cmds.append(f'G1 X{x} Y{y} Z{z}')
        elif Topology.is_circle(edge):
            curve = Topology.cast_curve(edge)
            arc = Arc(
                direction=Direction(curve.Axis().Direction()),
                position=Point(curve.Location()),
                radius=curve.Radius(),
                points=[topo.start_point, topo.end_point]
            )
            cmds.extend(generate_arc_gcode(arc, format_value))
        else:
            raise NotImplementedError("TODO: Cannot create gcode for wire")

    if not wire.description:
        wire.description = "Gcode: \n%s\n" % '\n'.join(cmds)

    return cmds



class Operation(Part):
    """ A single machining operation.

    """
    #: Set to True to disable this operation
    disabled = d_(Bool())

    #: Cutting tool
    tool = d_(Instance(Tool))

    #: Spindle control
    #: If zero off, if positive, CW, if negative CCW
    spindle_speed = d_(Float(strict=False))

    #: Dwell after spindle speed to allow time for ramp up/down
    spindle_dwell = d_(Float(1.0, strict=False))

    #: Feedrate of the operation
    feedrate = d_(Float(strict=False))

    #: Coolant control
    #: If mist or flood on, otherwise off
    coolant = d_(Enum('', 'mist', 'flood'))

    #: Starting point of operation
    start_point = d_(Coerced(Point, coercer=coerce_point))

    #: Ending point of operation
    end_point = d_(Coerced(Point, coercer=coerce_point))

    def _default_end_point(self):
        return self.start_point

    #: Generated gcode
    gcode = d_(Str())

    @d_func
    def generate_gcode(self) -> ListType[str]:
        cmds = []
        job = self.parent
        if self.feedrate:
            cmds.append(f"F{self.feedrate}")

        if self.spindle_speed:
            s = abs(self.spindle_speed)
            mcode = 'M3' if self.spindle_speed > 0 else 'M3'
            cmds.append(f'S{s} {mcode}')

            if self.spindle_dwell:
                pause = job.format_value(self.spindle_dwell)
                cmds.append(f'P{pause}') # Wait for spindle to ramp up

        if self.coolant == 'mist':
            cmds.append('M7')
        elif self.coolant == 'flood':
            cmds.append('M8')
        else:
            cmds.append(f'M9')

        return cmds

    def _default_gcode(self):
        return '\n'.join(self.generate_gcode())

    def _default_description(self):
        return "G-Code: \n" + self.gcode[0:100]
