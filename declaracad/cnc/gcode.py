"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 18, 2020

@author: jrm
"""
import os
import re
from collections import OrderedDict
from typing import Optional, Union

from atom.api import Atom, Bool, Float, Instance, Int, List, Str, Typed

from declaracad.occ.api import Point


def normalize(k: str, v: Union[int, float, str]) -> str:
    """Normalize an ID command"""
    vi = int(v)
    if v == vi:
        v = vi  # Clip off .0
    return f"{k}{v}"


class Waypoint(Atom):
    X = Float()
    Y = Float()
    Z = Float()
    A = Float()
    B = Float()
    C = Float()
    U = Float()
    V = Float()
    W = Float()


class Command(Atom):
    data = Instance(OrderedDict)
    id = Str()
    comment = Str()
    source = Str()
    lineno = Int()

    def _default_id(self) -> str:
        if self.data:
            for k, v in self.data.items():
                if k in GCode.ID_CODES:
                    return normalize(k, v)
        return ""

    waypoint = Typed(Waypoint)

    def _default_waypoint(self) -> Optional[Waypoint]:
        d = self.data
        if d:
            axis = {}
            for k in GCode.AXIS_CODES:
                if k in d:
                    axis[k] = d[k]
            if axis:
                return Waypoint(**axis)
        return None

    def position(self, last: Point, scale: float = 1) -> Point:
        """Get the 3D-position of this cmd's XYZ coordinates.

        Parameters
        ----------
        last: Point
            The previous position. Already converted!
        scale: float
            Scale for the units

        Returns
        -------
        point: Point
            The position of this command

        """
        data = self.data
        x = data.get("X")
        y = data.get("Y")
        z = data.get("Z")
        return Point(
            last.x if x is None else x * scale,
            last.y if y is None else y * scale,
            last.z if z is None else z * scale,
        )

    feedrate = Typed(float)

    def _default_feedrate(self) -> Optional[float]:
        if self.data and "F" in self.data:
            return float(self.data["F"])
        return None

    is_move = Bool()

    def _default_is_move(self) -> bool:
        return self.id in GCode.MOVE_CODES

    def __repr__(self) -> str:
        return "Command<{} from '{}' at line {}>".format(
            self.id, self.source, self.lineno
        )


class GCode(Atom):
    path = Str()
    commands = List(Command)

    AXIS_CODES = "XYZABCUVW"
    # Codes that will be put in their own command if their own single line
    ID_CODES = "GMTSPF"
    MOVE_CODES = ("G0", "G1", "G2", "G3", "G5", "G5.1")

    COLORMAP = {
        "G0": "green",
        "G1": "blue",
        "G2": "green",
        "G3": "green",
    }

    def __repr__(self) -> str:
        return "GCode<file='{} cmds=[\n    {}\n]>".format(
            self.path, ",\n    ".join(map(str, self.commands[0:100]))
        )

    def max(self) -> Point:
        """Return max value of each axis"""
        return Point(
            *(
                max(c.data[axis] for c in self.commands if c.data and axis in c.data)
                for axis in ("X", "Y", "Z")
            )
        )

    def min(self) -> Point:
        """Return min value of each axis"""
        return Point(
            *(
                min(c.data[axis] for c in self.commands if c.data and axis in c.data)
                for axis in ("X", "Y", "Z")
            )
        )


class Movement(Atom):
    rapid = Bool()
    points = List()

    def clone(self) -> "Movement":
        points = [Point(*p) for p in self.points]
        return Movement(rapid=self.rapid, points=points)


def convert(
    v: float, scale: float = 1, precision: Optional[int] = None, units: str = "mm"
) -> Union[int, float]:
    """Convert a value for writing to gcode

    Parameters
    ----------
    v: Float
        The value to convert
    scale: Float
        The scale to apply
    precision: None or Int
        The precision to apply, if 0 convert to integer, if None
        use full precision, otherwise round to given decimal places.

    Returns
    -------
    v: Int or Float
        The converted value

    """
    if units == "in":
        scale = scale * 1 / 25.4
    if precision == 0:
        return int(v * scale)
    elif precision is None:
        return v * scale
    return round(v * scale, precision)


def save_to_file(filename: str, movements: list[Movement], device):
    """Write to a file

    Parameters
    ----------
    filename: String
        The path to the file to save
    movements: List[Movement]
        List of movements to save
    device: Device
        Device to save it for
    """
    filename = os.path.abspath(os.path.expanduser(filename))
    save_dir = os.path.dirname(filename)
    if save_dir and not os.path.exists(save_dir):
        os.makedirs(save_dir)
    with open(filename, "w") as f:
        f.write("(Generated by DeclaraCAD)\n")
        f.write(f"(Path: {filename})\n")
        if device.config.init_commands:
            f.write(device.config.init_commands)
        if device.config.units:
            if device.config.units == "in":
                f.write("G20\n")
            else:
                f.write("G21\n")
        for movement in movements:
            cmd = "G0" if movement.rapid else "G1"
            for point in movement.points:
                x, y, z = device.convert(point)
                f.write(f"{cmd} X{x} Y{y} Z{z}\n")
        if device.config.finalize_commands:
            f.write(device.config.finalize_commands)


def parse(path: str) -> GCode:
    """Parse the file at the given path into a list of Commands

    Parameters
    ----------
    path: String
        The file path

    Notes
    -----
    This does not handle inline comments or multiple commands on a single line

    Returns
    -------
    gcode: GCode
        A GCode instance with the parsed commands

    """
    cmds: list[GCode] = []

    def set_id(cmd: Command) -> str:
        if not cmd.id:
            # If command is not specified use the last move
            for c in reversed(cmds):
                if c.is_move:
                    cmd.id = c.id
                    break
        return cmd.id

    def finish(cmd: Command):
        set_id(cmd)
        cmds.append(cmd)

    if os.path.exists(path):
        with open(path) as f:
            source = f.read()
    else:
        source = path
        path = "(source)"

    for i, line in enumerate(source.split("\n")):
        line = line.strip()
        if not line:
            continue

        # Strip comments
        parts = re.split(r";|\(|%", line, maxsplit=1)
        data = parts[0].strip()
        comment = "" if len(parts) == 1 else parts[1]
        if not data and not comment:
            continue

        cmd = Command(comment=comment, source=line, lineno=i + 1)
        if not data:
            cmds.append(cmd)  # Comment
            continue

        try:
            # Parse args
            args: list[tuple[str, float]] = []
            for c in re.findall(r"[A-z] *-?[\d.]+ *", data):
                args.append((c[0].upper(), float(c[1:])))

            # Since some files put mode changes on the same line
            # split them into separate commands
            d: dict[str, float] = OrderedDict()
            cmd.data = d
            for k, v in args:
                if k in d:
                    # HACK: Split out to a new command
                    # when duplicate keys are given in the same line, eg:
                    #     N40 G90 G00 X0 Y0
                    # is split into a G90 and G0
                    finish(cmd)
                    cmd = Command(comment=comment, source=line, lineno=i + 1)
                    cmd.data = d = OrderedDict()
                elif k in GCode.AXIS_CODES:
                    # HACK: If we get move arguments for a non-move split
                    # the command, eg a
                    #    N100 G01 X30 Y50
                    #    N110 G91 X10.1 Y-10.1
                    # should be split into a G1, G91, G1
                    cmd_id = set_id(cmd)
                    if cmd_id not in GCode.MOVE_CODES:
                        finish(cmd)
                        cmd = Command(comment=comment, source=line, lineno=i + 1)
                        cmd.data = d = OrderedDict()
                d[k] = v
            finish(cmd)
        except ValueError as e:
            filepath, filename = os.path.split(path)
            msg = "Failed to parse '%s' at line %s: %s" % (filename, i + 1, e)
            raise ValueError(msg)
    return GCode(path=path, commands=cmds)
