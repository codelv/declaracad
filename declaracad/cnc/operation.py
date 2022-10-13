"""
Copyright (c) 2021-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Nov 9, 2021

@author: jrm
"""
import traceback
from typing import Callable, Optional

import enaml
from atom.api import Bool, Coerced, Enum, Float, Instance, Str
from OCCT.Geom import Geom_Circle

from declaracad.occ.api import Arc, Direction, Part, Point, Polyline, Topology, Wire
from declaracad.occ.geom import coerce_point

with enaml.imports():
    from declaracad.cnc.cutters import Tool

from enaml.core.declarative import d_, d_func


def generate_arc_gcode(
    arc: Arc, format_value: Callable[[float], float], incremental: bool = True
) -> list[str]:
    """Generate gcodee for an Arc"""

    cmds = []
    d = arc.direction
    center = arc.position
    start, end = arc.topology.start_point, arc.topology.end_point
    delta = center - start if incremental else center
    x, y, z = map(format_value, end)
    if d == (0, 0, 1) or d == (0, 0, -1):
        axis = 2
        if arc.clockwise:
            code = "G3" if d[axis] == -1 else "G2"
        else:
            code = "G3" if d[axis] == 1 else "G2"
        # XY plane
        i, j = format_value(delta.x), format_value(delta.y)
        cmds.append(f"{code} X{x} Y{y} Z{z} I{i} J{j}")
    elif d == (0, 1, 0) or d == (0, -1, 0):
        axis = 1
        if arc.clockwise:
            code = "G3" if d[axis] == -1 else "G2"
        else:
            code = "G3" if d[axis] == 1 else "G2"
        # XZ plane
        i, k = format_value(delta.x), format_value(delta.z)
        cmds.append("G18 (XZ-plane)")
        cmds.append(f"{code} X{x} Z{z} Y{y} I{i} K{k}")
        cmds.append("G17 (XY-plane)")  # Restore G17
    elif d == (1, 0, 0) or d == (-1, 0, 0):
        axis = 0
        if arc.clockwise:
            code = "G3" if d[axis] == -1 else "G2"
        else:
            code = "G3" if d[axis] == 1 else "G2"

        # YZ plane
        j, k = format_value(delta.y), format_value(delta.z)
        cmds.append("G19 (YZ-plane)")
        cmds.append(f"{code} Y{y} Z{z} X{x} J{j} K{k}")
        cmds.append("G17 (XY-plane)")  # Restore G17
    else:
        raise NotImplementedError(f"Arc direction {d} cannot be converted")

    if not arc.description:
        arc.description = "Gcode: \n%s\n" % "\n".join(cmds)

    return cmds


def generate_polyline_gcode(
    polyline: Polyline, format_value: Callable[[float], float], rapid: bool = False
) -> list[str]:
    """Generate gcodee for a Polyline"""
    cmds = []
    code = "G0" if rapid else "G1"
    for p in polyline.points:
        x, y, z = map(format_value, p)
        cmds.append(f"{code} X{x} Y{y} Z{z}")
    return cmds


def generate_wire_gcode(
    wire: Wire, format_value: Callable[[float], float]
) -> list[str]:
    """Generate code for a Wire"""
    cmds = []
    last_point = wire.topology.start_point
    for edge in wire.topology.edges:
        topo = Topology(shape=edge)
        if Topology.is_line(edge):
            points = [topo.start_point, topo.end_point]
            for p in points:
                x, y, z = map(format_value, p)
                cmds.append(f"G1 X{x} Y{y} Z{z}")
            assert last_point == points[0]
            last_point = points[-1]
        elif Topology.is_circle(edge):
            curve: Geom_Circle = Topology.cast_curve(edge)
            points = [topo.start_point, topo.end_point]
            arc = Arc(
                direction=Direction(curve.Axis().Direction()),
                position=Point(curve.Location()),
                radius=curve.Radius(),
                clockwise=Topology.is_reversed(edge),
                points=points,
            )
            assert last_point == points[0]
            last_point = points[-1]
            cmds.extend(generate_arc_gcode(arc, format_value))
        else:
            raise NotImplementedError("TODO: Cannot create gcode for wire")

    if not wire.description:
        wire.description = "Gcode: \n%s\n" % "\n".join(cmds)

    return cmds


def generate_part_gcode(
    part: Part, format_value: Callable[[float], float]
) -> list[str]:
    """Generate code for a Part"""
    cmds: list[str] = []
    for child in part.children:
        if not getattr(child, "display", True):
            continue  # Do not render hidden items
        if hasattr(child, "generate_gcode"):
            cmds.extend(child.generate_gcode(format_value))
        elif isinstance(child, Polyline):
            rapid = child.name == "Rapid move"
            cmds.extend(generate_polyline_gcode(child, format_value, rapid))
        elif isinstance(child, Arc):
            cmds.extend(generate_arc_gcode(child, format_value))
        elif isinstance(child, Wire):
            cmds.extend(generate_wire_gcode(child, format_value))
        elif isinstance(child, Part):
            cmds.extend(generate_part_gcode(child, format_value))
    return cmds


class Operation(Part):
    """A single machining operation."""

    #: Set to True to disable this operation
    disabled = d_(Bool())

    #: Cutting tool
    tool = d_(Instance(Tool))

    #: Part being cut
    part = d_(Instance(Part))

    #: Spindle control
    #: If zero off, if positive, CW, if negative CCW
    spindle_speed = d_(Float(strict=False))

    #: Feedrate of the operation
    feedrate = d_(Float(strict=False))

    #: Surface speed
    #: Can be used to calculate default feedrate and spindle_speed
    surface_speed = d_(Float(strict=False))

    #: Coolant control
    #: If mist or flood on, otherwise off
    coolant = d_(Enum("", "mist", "flood"))

    #: Starting point of operation
    start_point = d_(Coerced(Point, coercer=coerce_point))

    #: Ending point of operation
    end_point = d_(Coerced(Point, coercer=coerce_point))

    #: Heading for gcode output
    operation_type = d_(Str())

    def _default_start_point(self):
        return self.parent.start_point

    def _default_end_point(self):
        return self.start_point

    #: Generated gcode
    gcode = d_(Str())

    @d_func
    def generate_spindle_start_gcode(
        self, format_value: Optional[Callable[[float], float]] = None
    ) -> list[str]:
        cmds = []

        # Turn on spindle and coolant from base operation
        s = abs(self.spindle_speed)
        mcode = "M3" if self.spindle_speed > 0 else "M3"
        cmds.append(f"S{s} {mcode}")

        if self.coolant == "mist":
            cmds.append("M7")
        elif self.coolant == "flood":
            cmds.append("M8")
        else:
            cmds.append("M9")
        return cmds

    @d_func
    def generate_toolpath_gcode(
        self, format_value: Callable[[float], float]
    ) -> list[str]:
        """Generate gcode output for this operation"""
        cmds = self.generate_spindle_start_gcode()
        cmds.extend(generate_part_gcode(self, format_value))
        if "M5" not in cmds:
            cmds.extend(self.generate_spindle_stop_gcode())
        return cmds

    @d_func
    def generate_spindle_stop_gcode(
        self, format_value: Optional[Callable[[float], float]] = None
    ) -> list[str]:
        cmds = []
        if self.coolant:
            # Turn off coolant
            cmds.append("M9")

        # Stop spindle it should have already retracted
        cmds.append("M5")
        return cmds

    @d_func
    def generate_gcode(
        self, format_value: Optional[Callable[[float], float]] = None
    ) -> list[str]:
        """Generate gcode output for this operation. If the disabled flag
        is set this just returns a comment.

        """
        if self.disabled:
            return [f"({self.operation_type} is disabled)"]

        job = self.parent
        format_value = format_value or job.format_value
        cmds = [f"({self.operation_type})"]
        try:
            # Change tool
            if self.tool:
                cmds.extend(self.tool.generate_gcode())

            if not self.spindle_speed:
                raise ValueError(
                    f"Spindle speed must be set for {self}. "
                    f"Use spindle_speed=value or set surface_speed=value "
                    f"to automatically calculate it."
                )

            if self.spindle_speed > job.max_spindle_speed:
                raise ValueError(
                    f"Spindle speed {self.spindle_speed} is above the "
                    f"machine limit {job.max_spindle_speed}"
                )

            if self.feedrate:
                cmds.append(f"F{self.feedrate}")

            cmds.extend(self.generate_toolpath_gcode(format_value))
            cmds.append("")  # Ensure newline
            return cmds
        except Exception as e:
            msg = f"(Error generating gcode: {e} for {self})"
            print(msg)
            traceback.print_exc()
            return [msg]

    def _default_gcode(self):
        return "\n".join(self.generate_gcode())

    def _default_description(self):
        return "G-Code: \n" + self.gcode[0:100]
