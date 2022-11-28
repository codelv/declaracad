"""
Copyright (c) 2018-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from typing import Optional

from atom.api import Bool, Typed
from enaml.colors import Color
from enaml.qt.qt_control import QtControl
from OCCT.gp import gp_Ax3
from OCCT.Graphic3d import Graphic3d_ClipPlane

from declaracad.occ.geom import Direction, Point
from declaracad.occ.impl.utils import color_to_quantity_color
from declaracad.viewer.widgets.occ_clipped_plane import ProxyOccViewerClippedPlane


class QtOccViewerClippedPlane(QtControl, ProxyOccViewerClippedPlane):

    #: Viewer widget
    clip_plane = Typed(Graphic3d_ClipPlane)

    #: Updates blocked
    _updates_blocked = Bool(True)

    def create_widget(self) -> None:
        self.clip_plane = Graphic3d_ClipPlane()

    def init_widget(self) -> None:
        # super(QtOccViewerClippedPlane, self).init_widget()
        d = self.declaration
        self.set_enabled(d.enabled)
        self.set_capping(d.capping)
        self.set_capping_hatched(d.capping_hatched)
        self.set_position(d.position)
        if d.capping_color:
            self.set_capping_color(d.capping_color)

    def init_layout(self) -> None:
        self._updates_blocked = False
        viewer = self.parent()
        clip_plane = self.clip_plane
        viewer.v3d_view.AddClipPlane(clip_plane)
        # for ais_shp in viewer._ais_shapes:
        #    ais_shp.AddClipPlane(clip_plane)
        self.update_viewer()

    def destroy(self) -> None:
        viewer = self.parent()
        clip_plane = self.clip_plane
        clip_plane.SetOn(False)
        if viewer is not None:
            viewer.v3d_view.RemoveClipPlane(clip_plane)
            # for ais_shp in viewer._ais_shapes:
            #    try:
            #        ais_shp.RemoveClipPlane(clip_plane)
            #    except:
            #        pass
        del self.clip_plane
        super(QtOccViewerClippedPlane, self).destroy()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def update_viewer(self) -> None:
        if self._updates_blocked:
            return
        self.parent().ais_context.UpdateCurrentViewer()

    # -------------------------------------------------------------------------
    # ProxyOccViewerCappedPlane API
    # -------------------------------------------------------------------------
    def set_enabled(self, enabled: bool):
        self.clip_plane.SetOn(enabled)
        self.update_viewer()

    def set_capping(self, capping: bool):
        self.clip_plane.SetCapping(capping)
        self.update_viewer()

    def set_capping_hatched(self, hatched: bool):
        if hatched:
            self.clip_plane.SetCappingHatchOn()
        else:
            self.clip_plane.SetCappingHatchOff()
        self.update_viewer()

    def set_capping_color(self, color: Optional[Color]) -> None:
        if not color:
            return
        c, t = color_to_quantity_color(color)
        clip_plane = self.clip_plane
        mat = clip_plane.CappingMaterial()
        mat.SetAmbientColor(c)
        mat.SetDiffuseColor(c)
        clip_plane.SetCappingMaterial(mat)

    def _update_position(
        self,
        position: Point,
        direction: Direction,
    ):
        clip_plane = self.clip_plane
        pln = clip_plane.ToPlane()
        pln.SetPosition(gp_Ax3(position.proxy, direction.proxy))
        clip_plane.SetEquation(pln)
        self.update_viewer()

    def set_position(self, position: Point):
        self._update_position(position, self.declaration.direction)

    def set_direction(self, direction: Direction):
        self._update_position(self.declaration.position, direction)
