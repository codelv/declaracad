"""
Copyright (c) 2018-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Typed, Bool

from enaml.qt.qt_control import QtControl

from OCCT.gp import gp_Pnt, gp_Dir, gp_Ax3
from OCCT.Graphic3d import Graphic3d_ClipPlane, Graphic3d_MaterialAspect

from declaracad.core.utils import log
from declaracad.occ.impl.utils import color_to_quantity_color
from declaracad.viewer.widgets.occ_clipped_plane import ProxyOccViewerClippedPlane


class QtOccViewerClippedPlane(QtControl, ProxyOccViewerClippedPlane):

    #: Viewer widget
    clip_plane = Typed(Graphic3d_ClipPlane)

    #: Updates blocked
    _updates_blocked = Bool(True)

    def create_widget(self):
        self.clip_plane = Graphic3d_ClipPlane()

    def init_widget(self):
        #super(QtOccViewerClippedPlane, self).init_widget()
        d = self.declaration
        clip_plane = self.clip_plane
        self.set_enabled(d.enabled)
        self.set_capping(d.capping)
        self.set_capping_hatched(d.capping_hatched)
        self.set_position(d.position)
        if d.capping_color:
            self.set_capping_color(d.capping_color)

    def init_layout(self):
        self._updates_blocked = False
        viewer = self.parent()
        clip_plane = self.clip_plane
        viewer.v3d_view.AddClipPlane(clip_plane)
        #for ais_shp in viewer._ais_shapes:
        #    ais_shp.AddClipPlane(clip_plane)
        self.update_viewer()

    def destroy(self):
        viewer = self.parent()
        clip_plane = self.clip_plane
        clip_plane.SetOn(False)
        if viewer is not None:
            viewer.v3d_view.RemoveClipPlane(clip_plane)
            #for ais_shp in viewer._ais_shapes:
            #    try:
            #        ais_shp.RemoveClipPlane(clip_plane)
            #    except:
            #        pass
        del self.clip_plane
        super(QtOccViewerClippedPlane, self).destroy()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def update_viewer(self):
        if self._updates_blocked:
            return
        self.parent().ais_context.UpdateCurrentViewer()

    # -------------------------------------------------------------------------
    # ProxyOccViewerCappedPlane API
    # -------------------------------------------------------------------------
    def set_enabled(self, enabled):
        self.clip_plane.SetOn(enabled)
        self.update_viewer()

    def set_capping(self, capping):
        self.clip_plane.SetCapping(capping)
        self.update_viewer()

    def set_capping_hatched(self, hatched):
        if hatched:
            self.clip_plane.SetCappingHatchOn()
        else:
            self.clip_plane.SetCappingHatchOff()
        self.update_viewer()

    def set_capping_color(self, color):
        if not color:
            return
        c, t = color_to_quantity_color(color)
        clip_plane = self.clip_plane
        mat = clip_plane.CappingMaterial()
        mat.SetAmbientColor(c)
        mat.SetDiffuseColor(c)
        clip_plane.SetCappingMaterial(mat)

    def set_position(self, position, direction=None):
        d = self.declaration
        direction = direction or d.direction
        clip_plane = self.clip_plane
        pln = clip_plane.ToPlane()
        pln.SetPosition(gp_Ax3(gp_Pnt(*position), gp_Dir(*direction)))
        clip_plane.SetEquation(pln)
        self.update_viewer()

    def set_direction(self, direction):
        self.set_position(self.declaration.position, direction)
