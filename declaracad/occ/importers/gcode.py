"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
import cmath
from declaracad.cnc import gcode
from declaracad.occ.api import Vertex, Point, Polyline, Bezier, Arc, Wire, Circle
from declaracad.core.utils import log

COLORMAP = {
    "rapid": "green",
    "normal": "red",
    "arc": "orange",
    "plunge": "blue",
}


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
    items = []

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
    plane = 'xy'
    for cmd in doc.commands:
        data = cmd.data
        if cmd.id in ("G0", "G1"):
            if mode == "absolute":
                pos = cmd.position(last)
            else:
                pos = last + cmd.position(zero)

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
                    Polyline(points=[last, pos], description=cmd.source, color=color)
                )
            last = pos
            last_cmd = cmd
            last_color = color
        elif cmd.id == "G17":
            plane = 'xy'
        elif cmd.id == "G18":
            plane = 'xz'
        elif cmd.id == "G19":
            plane = 'yz'
        elif cmd.id in ("G2", "G3"):
            # TODO: Helical arcs using Z is not implemented
            pos = cmd.position(last)
            clockwise = cmd.id == "G2"
            r = data.get("R")
            if r is not None:
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
                        position=center,
                        radius=r,
                        clockwise=clockwise,
                        points=[last, pos],
                        color=arc_color,
                        description=cmd.source,
                    )
                )
            # elif 'U' in data:
            else:
                # Center format
                i, j, k = data.get("I"), data.get("J"), data.get("K")

                if "P" in data:
                    raise NotImplementedError(f"Helix is not implemented {cmd}")

                if plane == 'xy':
                    if i is None and j is None:
                        raise ValueError(f"Invalid arc {cmd} (both I and J missing)")
                    direction = (0, 0, 1)
                    center = last + (i or 0, j or 0)
                elif plane == 'xz':
                    if i is None and k is None:
                        raise ValueError(f"Invalid arc {cmd} (both I and K missing)")
                    direction = (0, 1, 0)
                    center = last + (i or 0, 0, k or 0)
                elif plane == 'yz':
                    if k is None and j is None:
                        raise ValueError(f"Invalid arc {cmd} (both J and K missing)")
                    direction = (1, 0, 0)
                    center = last + (0, j or 0, k or 0)
                else:
                    raise RuntimeError("Unreachable code. This is likely a bug")
                r = center.distance(last)
                r2 = center.distance(pos)
                #if abs(r2-r) > 1e-3:
                #    raise ValueError(f"Arc start and end do not match {r} != {r2}")

                items.append(
                    Arc(
                        direction=direction,
                        position=center,
                        radius=r,
                        clockwise=clockwise,
                        points=[last, pos],
                        color=arc_color,
                        description=cmd.source,
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
            points = [last, last + Point(data["X"], data["Y"])]

            # For first
            if last_cmd.id != "G5":
                points.append(points[-1] + Point(data["I"], data["J"]))
            elif "I" in data and "J" in data:
                points.append(points[-1] + Point(data["I"], data["J"]))
            elif "I" in data or "J" in data:
                # Must both be specified or nether
                raise ValueError(f"Incomplete G5 command {cmd}")

            # Last point
            points.append(points[-1] + Point(cmd["P"], cmd["Q"]))

            items.append(
                Bezier(
                    points=points,
                    color=normal_color,
                    description=cmd.source,
                )
            )
            last = points[-1]
            last_cmd = cmd
        elif cmd.id == "G5.1":
            c1 = last + Point(data["X"], data["Y"])
            i, j = data.get("I"), data.get("J")
            if i is None and j is None:
                raise ValueError(f"Incomplete G5.1 command {cmd}")
            c2 = c1 + Point(i or 0, j or 0)
            items.append(
                Bezier(
                    points=[last, c1, c2],
                    color=normal_color,
                    description=cmd.source,
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

    return items
