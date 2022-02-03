"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
import cmath

import enaml

from declaracad.cnc import gcode
from declaracad.core.utils import log
from declaracad.occ.api import (Arc, Bezier, Circle, Direction, Point,
                                Polyline, Vertex, Wire)

with enaml.imports():
    from declaracad.parts.display import Axis, BoundingBox


COLORMAP = {
    "rapid": "green",
    "normal": "red",
    "arc": "orange",
    "plunge": "blue",
}


def normal_direction(plane: str) -> Direction:
    """Get the normal direction for the given plane."""
    if plane == "xy":
        return Direction(0, 0, 1)
    elif plane == "xz":
        return Direction(0, 1, 0)
    elif plane == "yz":
        return Direction(1, 0, 0)
    else:
        raise ValueError(f"Unknown plane direction {plane}")


def load_gcode(filename, **options):
    """Load a GCode file into a list of shapes to render

    Parameters
    ----------
    filename: String
        The file path to load
    options: Dict
        merge_points: Bool
            If true, connected merge line segments of the same command into
            a single polyline (faster but doesn't show individual commands).
        colors: Dict
            A dict to update the colormap

    Returns
    -------
    toolpath: List[Shape]
        List of shapes to visualize the toolpath

    """
    doc = gcode.parse(filename)
    start = Point(0, 0, 0)
    last = start
    items = [Axis()]

    #
    merge_points = options.get("merge_points", True)

    # Add color options
    colors = COLORMAP.copy()
    if "colors" in options:
        colors.update(options["colors"])
    rapid_color = colors["rapid"]
    normal_color = colors["normal"]
    arc_color = colors["arc"]
    plunge_color = colors["plunge"]

    zero = Point()
    last_color = None
    last_cmd = gcode.Command()
    mode = "absolute"
    log.debug(doc)
    plane = "xy"
    units = options.get("units", "mm")
    feedrate = options.get("feedrate", 0)
    scale = 25.4 if units == "in" else 1
    for cmd in doc.commands:
        data = cmd.data
        if cmd.id in ("G0", "G1"):
            if mode == "absolute":
                pos = cmd.position(last, scale)
            else:
                pos = last + cmd.position(zero, scale)

            if last == pos:
                log.debug(f"Duplicate: {cmd}")
                continue
            if cmd.id == "G0":
                color = rapid_color
            elif last_cmd and last_cmd.id == "G0":
                color = plunge_color
            else:
                color = normal_color

            if "R" in data:
                # Radius'd corner
                # TODO: THIS
                log.warning(f"Radius ignored: {cmd}")

            if merge_points and last_cmd.id == cmd.id and color == last_color:
                items[-1].points.append(pos)
            else:
                # Start a new one
                items.append(
                    Polyline(
                        points=[last, pos],
                        description=f"Gcode: {cmd.source}",
                        color=color,
                        line_style="dashed" if cmd.id == "G0" else "solid",
                    )
                )
            last = pos
            last_cmd = cmd
            last_color = color
        elif cmd.id == "G17":
            plane = "xy"
        elif cmd.id == "G18":
            plane = "xz"
        elif cmd.id == "G19":
            plane = "yz"
        elif cmd.id == "G20":
            units = "in"
            scale = 25.4
        elif cmd.id == "G21":
            units = "mm"
            scale = 1
        elif cmd.id in ("G2", "G3"):
            # TODO: Helical arcs using Z is not implemented
            pos = cmd.position(last, scale)
            clockwise = cmd.id == "G2"
            r = data.get("R")
            if r is not None:
                r *= scale

                # Solve for center
                delta = pos - last
                if delta.z != 0:
                    raise NotImplementedError(f"Helix is not implemented {cmd}")
                midpoint = pos.midpoint(last)
                q = pos.distance(last)
                if q == 0:
                    raise ValueError(f"Invalid command {cmd} (d=0)")

                u = cmath.sqrt(r ** 2 - (q / 2) ** 2)
                if clockwise:
                    u = -u
                x = (midpoint.x - u * delta.y / q).real
                y = (midpoint.y + u * delta.x / q).real

                center = Point(x, y, pos.z)
                items.append(
                    Arc(
                        direction=normal_direction(plane),
                        position=center,
                        radius=r,
                        clockwise=clockwise,
                        points=[last, pos],
                        color=arc_color,
                        description=f"Gcode: {cmd.source}",
                    )
                )
            # elif 'U' in data:
            else:
                # Center format
                i, j, k = data.get("I"), data.get("J"), data.get("K")

                if "P" in data:
                    raise NotImplementedError(f"Helix is not implemented {cmd}")

                helix = 0
                if plane == "xy":
                    if i is None and j is None:
                        raise ValueError(f"Invalid arc {cmd} (both I and J missing)")
                    center = last + (i * scale or 0, j * scale or 0)
                    z = data.get("Z")
                    if z is not None:
                        helix = z * scale - last.z
                elif plane == "xz":
                    if i is None and k is None:
                        raise ValueError(f"Invalid arc {cmd} (both I and K missing)")
                    center = last + (i * scale or 0, 0, k * scale or 0)
                    y = data.get("Y")
                    if y is not None:
                        helix = y * scale - last.y
                elif plane == "yz":
                    if k is None and j is None:
                        raise ValueError(f"Invalid arc {cmd} (both J and K missing)")
                    center = last + (0, j * scale or 0, k * scale or 0)
                    x = data.get("X")
                    if x is not None:
                        helix = x * scale - last.x
                else:
                    raise RuntimeError("Unreachable code. This is likely a bug")
                r = center.distance(last)
                r2 = center.distance(pos)
                # if abs(r2-r) > 1e-3:
                #      print(f"Warning: Arc start and end do not match {r} != {r2}")

                direction = normal_direction(plane)
                helical = abs(helix) > 1e-6
                if helical:
                    # Recompute direction, center, and radius
                    pitch = helix * 4
                    b = helix / 2
                    r = cmath.sqrt(r ** 2 + helix ** 2).real
                    if plane == "xy":
                        rot = 1 if i > 0 else -1
                        center = center + (0, 0, b)
                        direction = (rot * -b, 0, r)
                    elif plane == "xz":
                        rot = 1 if k > 0 else -1
                        center = center + (0, b, 0)
                        direction = (rot * -b, r, 0)
                    elif plane == "yz":
                        rot = 1 if j > 0 else -1
                        center = center + (b, 0, 0)
                        direction = (r, 0, rot * -b)
                    else:
                        assert False, "Unreachable"

                items.append(
                    Arc(
                        direction=direction,
                        position=center,
                        radius=r,
                        clockwise=clockwise,
                        points=[last, pos],
                        color=arc_color,
                        description="".join(
                            [
                                "Helical\n  " if helical else "",
                                f"Plane {plane.upper()}\n  ",
                                f"Gcode: {cmd.source}",
                            ]
                        ),
                    )
                )
            last = pos
            last_cmd = cmd
        elif cmd.id == "G4":
            t = cmd.data.get("P")
            if not t or t < 0:
                raise ValueError(f"Invalid dwell time {cmd}")
            items.append(
                Vertex(
                    position=last,
                    description=f"Dwell {t}s",
                )
            )
            last_cmd = cmd
        elif cmd.id == "G5":
            # Cubic B-Spline
            points = [last, last + Point(data["X"] * scale, data["Y"] * scale)]

            # For first
            if last_cmd.id != "G5":
                points.append(points[-1] + Point(data["I"] * scale, data["J"] * scale))
            elif "I" in data and "J" in data:
                points.append(points[-1] + Point(data["I"] * scale, data["J"] * scale))
            elif "I" in data or "J" in data:
                # Must both be specified or nether
                raise ValueError(f"Incomplete G5 command {cmd}")

            # Last point
            points.append(points[-1] + Point(cmd["P"] * scale, cmd["Q"] * scale))

            items.append(
                Bezier(
                    points=points,
                    color=normal_color,
                    description=f"Gcode: {cmd.source}",
                )
            )
            last = points[-1]
            last_cmd = cmd
        elif cmd.id == "G5.1":
            c1 = last + Point(data["X"] * scale, data["Y"] * scale)
            i, j = data.get("I"), data.get("J")
            if i is None and j is None:
                raise ValueError(f"Incomplete G5.1 command {cmd}")
            c2 = c1 + Point(i * scale or 0, j * scale or 0)
            items.append(
                Bezier(
                    points=[last, c1, c2],
                    color=normal_color,
                    description=f"Gcode: {cmd.source}",
                )
            )
            last_cmd = cmd
            last = c2
        elif cmd.id == "G90":
            mode = "absolute"
        elif cmd.id == "G91":
            mode = "incremental"
        else:
            log.debug(f"Ignoring: {cmd}")

    # Show bbox?
    # bbox = BoundingBox(shapes=items[1:])
    # items.append(bbox)

    return items
