"""
Copyright (c) 2018-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

@author: jrm
"""
from typing import Any

from atom.api import Bool, Float, ForwardTyped, Tuple, Typed, observe
from enaml.colors import Color, ColorMember
from enaml.core.declarative import d_
from enaml.widgets.control import Control, ProxyControl


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

    def set_position(self, position: tuple[float, float, float]):
        raise NotImplementedError

    def set_direction(self, direction: tuple[float, float, float]):
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
    position = d_(Tuple(Float(strict=False), default=(0, 0, 0)))

    #: Direction
    direction = d_(Tuple(Float(strict=False), default=(1, 0, 0)))

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
