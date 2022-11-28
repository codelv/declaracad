"""
Copyright (c) 2018-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

@author: jrm
"""
from typing import Any

from atom.api import Bool, Coerced, ForwardTyped, Typed, observe
from enaml.colors import Color, ColorMember
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl

from declaracad.occ.geom import Direction, Point, coerce_direction, coerce_point


class ProxyOccViewerClippedPlane(ProxyControl):
    #: A reference to the ClippedPlane declaration.
    declaration = ForwardTyped(lambda: OccViewerClippedPlane)

    def set_enabled(self, enabled: bool):
        raise NotImplementedError

    def set_capping(self, enabled: bool):
        raise NotImplementedError

    def set_capping_hashed(self, enabled: bool):
        raise NotImplementedError

    def set_capping_color(self, color: Color):
        raise NotImplementedError

    def set_position(self, position: Point):
        raise NotImplementedError

    def set_direction(self, direction: Direction):
        raise NotImplementedError


class OccViewerClippedPlane(Control):
    #: A reference to the ProxySpinBox object.
    proxy = Typed(ProxyOccViewerClippedPlane)

    #: Enabled
    enabled = d_(Bool(True))

    #: Capping
    capping = d_(Bool(True))

    #: Hatched
    capping_hatched = d_(Bool(True))

    #: Color
    capping_color = d_(ColorMember())

    #: Position
    position = d_(Coerced(Point, coercer=coerce_point))

    def _default_position(self):
        return Point()

    #: Direction
    direction = d_(Coerced(Direction, coercer=coerce_direction))

    def _default_direction(self):
        return Direction(1, 0, 0)

    # -------------------------------------------------------------------------
    # Observers
    # -------------------------------------------------------------------------
    @observe(
        "position",
        "direction",
        "enabled",
        "capping",
        "capping_hatched",
        "capping_color",
    )
    def _update_proxy(self, change: dict[str, Any]):
        """An observer which sends state change to the proxy."""
        # The superclass handler implementation is sufficient.
        super(OccViewerClippedPlane, self)._update_proxy(change)
