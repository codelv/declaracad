"""
Copyright (c) 2018-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

@author: jrm
"""
from atom.api import Bool, Typed, ForwardTyped, Tuple, Float, observe
from enaml.core.declarative import d_
from enaml.colors import ColorMember
from enaml.widgets.control import Control, ProxyControl


class ProxyOccViewerClippedPlane(ProxyControl):
    #: A reference to the ClippedPlane declaration.
    declaration = ForwardTyped(lambda: OccViewerClippedPlane)

    def set_enabled(self, enabled):
        raise NotImplementedError

    def set_capping(self, enabled):
        raise NotImplementedError

    def set_capping_hashed(self, enabled):
        raise NotImplementedError

    def set_capping_color(self, color):
        raise NotImplementedError

    def set_position(self, position):
        raise NotImplementedError

    def set_direction(self, direction):
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
    @observe('position', 'direction', 'enabled', 'capping', 'capping_hatched',
             'capping_color')
    def _update_proxy(self, change):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super(OccViewerClippedPlane, self)._update_proxy(change)

