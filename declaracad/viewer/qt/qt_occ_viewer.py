"""
Copyright (c) 2016-2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 26, 2016

"""
import os
import sys
from contextlib import contextmanager
from typing import Any, Optional

from atom.api import Bool, Dict, Int, List, Property, Typed
from enaml.application import Application
from enaml.colors import Color
from enaml.qt import QtGui
from enaml.qt.qt_control import QtControl
from enaml.qt.QtCore import Qt, QTimer
from enaml.qt.QtGui import QPalette
from enaml.qt.QtWidgets import QOpenGLWidget
from OCCT import Aspect, TopAbs, V3d
from OCCT.AIS import (
    AIS_DisplayMode,
    AIS_InteractiveContext,
    AIS_Shaded,
    AIS_Shape,
    AIS_WireFrame,
)
from OCCT.Aspect import (
    Aspect_DisplayConnection,
    Aspect_GFM_VER,
    Aspect_GridDrawMode,
    Aspect_GridType,
)
from OCCT.Bnd import Bnd_Box
from OCCT.BRepBndLib import BRepBndLib
from OCCT.Graphic3d import (
    Graphic3d_Camera,
    Graphic3d_RenderingParams,
    Graphic3d_RM_RASTERIZATION,
    Graphic3d_RM_RAYTRACING,
    Graphic3d_StereoMode_QuadBuffer,
    Graphic3d_Structure,
    Graphic3d_StructureManager,
    Graphic3d_TypeOfShadingModel,
)
from OCCT.MeshVS import MeshVS_Mesh, MeshVS_MeshEntityOwner
from OCCT.OpenGl import OpenGl_GraphicDriver
from OCCT.Prs3d import Prs3d_Drawer
from OCCT.PrsMgr import PrsMgr_PresentationManager
from OCCT.Quantity import Quantity_Color, Quantity_NOC_BLACK, Quantity_NOC_WHITE
from OCCT.TCollection import TCollection_AsciiString
from OCCT.TopoDS import TopoDS_Shape
from OCCT.V3d import (
    V3d_AmbientLight,
    V3d_DirectionalLight,
    V3d_SpotLight,
    V3d_TypeOfOrientation,
    V3d_View,
    V3d_Viewer,
)

from declaracad.core.utils import log
from declaracad.occ.api import BBox, Shape
from declaracad.occ.impl.occ_dimension import OccDimension
from declaracad.occ.impl.occ_display import OccDisplayItem
from declaracad.occ.impl.occ_shape import OccPart, OccShape
from declaracad.occ.impl.utils import color_to_quantity_color
from declaracad.viewer.widgets.occ_viewer import (
    LineAspect,
    ProxyOccViewer,
    ViewerSelection,
)

if sys.platform == "win32":
    from OCCT.WNT import WNT_Window

    V3d_Window = WNT_Window
elif sys.platform == "darwin":
    from OCCT.Cocoa import Cocoa_Window

    V3d_Window = Cocoa_Window
else:
    from OCCT.Xw import Xw_Window

    V3d_Window = Xw_Window


V3D_VIEW_MODES: dict[str, V3d_TypeOfOrientation] = {
    "top": V3d.V3d_Zpos,
    "bottom": V3d.V3d_Zneg,
    "left": V3d.V3d_Xneg,
    "right": V3d.V3d_Xpos,
    "front": V3d.V3d_Yneg,
    "back": V3d.V3d_Ypos,
    "iso": V3d.V3d_XposYnegZpos,
}

V3D_DISPLAY_MODES: dict[str, AIS_DisplayMode] = {
    "shaded": AIS_Shaded,
    "wireframe": AIS_WireFrame,
}

BLACK = Quantity_Color(Quantity_NOC_BLACK)
WHITE = Quantity_Color(Quantity_NOC_WHITE)

SelectionInfoType = dict[str, dict[int, OccShape]]


class QtViewer3d(QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._lock_rotation = False
        self._lock_zoom = False
        self._drawbox = None
        self._zoom_area = False
        self._select_area = False
        self._inited = False
        self._leftisdown = False
        self._middleisdown = False
        self._rightisdown = False
        self._selection = None
        self._drawtext = True
        self._select_pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 2)
        self._callbacks = {
            "key_pressed": [],
            "mouse_dragged": [],
            "mouse_scrolled": [],
            "mouse_moved": [],
            "mouse_pressed": [],
            "mouse_released": [],
        }
        self.proxy = None
        self._last_code = None

        # enable Mouse Tracking
        self.setMouseTracking(True)
        # Strong focus
        self.setFocusPolicy(Qt.StrongFocus)

        # required for overpainting the widget
        self.setAutoFillBackground(False)
        self.setBackgroundRole(QPalette.NoRole)
        self.setAttribute(Qt.WA_PaintOnScreen)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def get_window_id(self):
        """Returns an the identifier of the GUI widget."""
        hwnd = self.winId()
        if sys.platform == "win32":
            import ctypes

            ctypes.pythonapi.PyCapsule_New.restype = ctypes.py_object
            ctypes.pythonapi.PyCapsule_New.argtypes = [
                ctypes.c_int,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ]
            return ctypes.pythonapi.PyCapsule_New(hwnd, None, None)
        return hwnd

    def resizeEvent(self, event):
        view = self.proxy.v3d_view
        if view:
            view.MustBeResized()

    def keyPressEvent(self, event):
        if self.hasFocus():
            self._fire_event("key_pressed", event)

    def focusInEvent(self, event):
        self.proxy.v3d_view.Redraw()

    def focusOutEvent(self, event):
        self.proxy.v3d_view.Redraw()

    def paintEvent(self, event):
        self.proxy.v3d_view.Redraw()

    def initializeGL(self):
        self.proxy.init_viewer()

    def resizeGL(self):
        self.proxy.v3d_view.MustBeResized()

    def wheelEvent(self, event):
        if self._fire_event("mouse_scrolled", event):
            return
        if self._lock_zoom:
            return
        delta = event.angleDelta().y()  # PyQt5
        view = self.proxy.v3d_view
        view.Redraw()
        view.SetZoom(1.25 if delta > 0 else 0.8)

    def dragMoveEvent(self, event):
        if self._fire_event("mouse_dragged", event):
            return

    def _fire_event(self, name, event):
        handled = False
        view = self.proxy.v3d_view
        for cb in self._callbacks.get(name, []):
            # Raise StopIteration to ignore the default handlers
            try:
                cb((view, event))
            except StopIteration:
                handled = True
            except Exception as e:
                log.exception(e)
        return handled

    def mousePressEvent(self, event):
        self.setFocus()
        pos = self.dragStartPos = event.pos()
        if self._fire_event("mouse_pressed", event):
            return
        self.proxy.v3d_view.StartRotation(pos.x(), pos.y())

    def mouseReleaseEvent(self, event):
        if self._fire_event("mouse_released", event):
            return
        view = self.proxy.v3d_view
        btn = event.button()

        if btn == Qt.LeftButton:
            pt = event.pos()
            pos = (pt.x(), pt.y())
            shift = event.modifiers() == Qt.ShiftModifier
            area = self._drawbox if self._select_area else None
            self.proxy.update_selection(pos=pos, area=area, shift=shift)
            if area:
                self._select_area = False
        elif btn == Qt.RightButton:
            if self._zoom_area:
                xmin, ymin, dx, dy = self._drawbox
                view.WindowFit(xmin, ymin, xmin + dx, ymin + dy)
                self._zoom_area = False

    def draw_box(self, event):
        tolerance = 2
        pt = event.pos()
        start = self.dragStartPos
        sx, sy = start.x(), start.y()
        dx, dy = pt.x() - sx, pt.y() - start.y()
        if abs(dx) <= tolerance and abs(dy) <= tolerance:
            return
        self._drawbox = (sx, sy, dx, dy)

    def mouseMoveEvent(self, event):
        if self._fire_event("mouse_moved", event):
            return
        pt = event.pos()
        buttons = event.buttons()
        modifiers = event.modifiers()
        view = self.proxy.v3d_view
        # ROTATE
        if buttons == Qt.LeftButton:
            # dx = pt.x() - self.dragStartPos.x()
            # dy = pt.y() - self.dragStartPos.y()
            if not self._lock_rotation:
                view.Rotation(pt.x(), pt.y())
            self._drawbox = None
        # DYNAMIC ZOOM
        elif buttons == Qt.RightButton and not modifiers == Qt.ShiftModifier:
            view.Redraw()
            view.Zoom(
                abs(self.dragStartPos.x()),
                abs(self.dragStartPos.y()),
                abs(pt.x()),
                abs(pt.y()),
            )
            self.dragStartPos = pt
            self._drawbox = None
        # PAN
        elif buttons == Qt.MouseButton.MiddleButton:
            dx = pt.x() - self.dragStartPos.x()
            dy = pt.y() - self.dragStartPos.y()
            self.dragStartPos = pt
            view.Pan(dx, -dy)
            self._drawbox = None
        # DRAW BOX
        # ZOOM WINDOW
        elif buttons == Qt.RightButton and modifiers == Qt.ShiftModifier:
            self._zoom_area = True
            self.draw_box(event)
        # SELECT AREA
        elif buttons == Qt.LeftButton and modifiers == Qt.ShiftModifier:
            self._select_area = True
            self.draw_box(event)
        else:
            self._drawbox = None
            ais_context = self.proxy.ais_context
            ais_context.MoveTo(pt.x(), pt.y(), view, True)


class QtOccViewer(QtControl, ProxyOccViewer):

    #: Viewer widget
    widget = Typed(QtViewer3d)

    #: Use view animations
    animations = Bool()

    #: Update count
    _redraw_blocked = Bool()

    #: Displayed Shapes
    _displayed_shapes = Dict(TopoDS_Shape, OccShape)
    _displayed_dimensions = Dict()
    _displayed_graphics = Dict()
    _selected_shapes = List()

    #: Errors
    errors = Dict()

    #: Grid colors
    grid_colors = Dict()

    #: Shapes
    shapes = Property(lambda self: self.get_shapes(), cached=True)

    #: Dimensions
    dimensions = Typed(set)
    graphics = Typed(set)

    # -------------------------------------------------------------------------
    # OpenCascade specific members
    # -------------------------------------------------------------------------
    display_connection = Typed(Aspect_DisplayConnection)
    v3d_viewer = Typed(V3d_Viewer)
    v3d_view = Typed(V3d_View)

    ais_context = Typed(AIS_InteractiveContext)
    prs3d_drawer = Typed(Prs3d_Drawer)
    prs_mgr = Typed(PrsMgr_PresentationManager)
    v3d_window = Typed(V3d_Window)
    gfx_structure_manager = Typed(Graphic3d_StructureManager)
    gfx_structure = Typed(Graphic3d_Structure)
    graphics_driver = Typed(OpenGl_GraphicDriver)
    camera = Typed(Graphic3d_Camera)

    #: List of lights
    lights = List()

    #: Fired
    _redisplay_timer = Typed(QTimer, ())

    _qt_app = Property(lambda self: Application.instance()._qapp, cached=True)

    #: Max msaa samples
    msaa_samples = Int(0)

    def get_shapes(self):
        return [c for c in self.children() if not isinstance(c, QtControl)]

    def create_widget(self):
        self.widget = QtViewer3d(parent=self.parent_widget())

    def init_widget(self):
        super().init_widget()
        widget = self.widget
        widget.proxy = self

        redisplay_timer = self._redisplay_timer
        redisplay_timer.setSingleShot(True)
        redisplay_timer.setInterval(8)
        redisplay_timer.timeout.connect(self.on_redisplay_requested)

    def init_viewer(self):
        """Init viewer when the QOpenGLWidget is ready"""
        d = self.declaration
        widget = self.widget
        if sys.platform == "win32":
            display = Aspect_DisplayConnection()
        else:
            DISPLAY = os.environ.get("DISPLAY", "0")
            display_name = TCollection_AsciiString(DISPLAY)
            display = Aspect_DisplayConnection(display_name)
        self.display_connection = display

        # Create viewer
        graphics_driver = self.graphics_driver = OpenGl_GraphicDriver(display)

        viewer = self.v3d_viewer = V3d_Viewer(graphics_driver)
        viewer.SetDefaultShadingModel(
            Graphic3d_TypeOfShadingModel.Graphic3d_TOSM_FRAGMENT
        )
        view = self.v3d_view = viewer.CreateView()

        # Setup window
        win_id = widget.get_window_id()
        if sys.platform == "win32":
            window = WNT_Window(win_id)
        elif sys.platform == "darwin":
            window = Cocoa_Window(win_id)
        else:
            window = Xw_Window(self.display_connection, win_id)
        if not window.IsMapped():
            window.Map()
        self.v3d_window = window
        view.SetWindow(window)
        view.MustBeResized()

        # Setup viewer
        ais_context = self.ais_context = AIS_InteractiveContext(viewer)
        self.prs3d_drawer = ais_context.DefaultDrawer()

        # Needed for displaying graphics
        prs_mgr = self.prs_mgr = ais_context.MainPrsMgr()
        gfx_mgr = self.gfx_structure_manager = prs_mgr.StructureManager()
        self.gfx_structure = Graphic3d_Structure(gfx_mgr)

        # Dump gl info and grab msaa
        self.dump_gl_info()

        # Lights camera
        self.camera = view.Camera()

        try:
            self.set_lights(d.lights)
        except Exception as e:
            log.exception(e)
            viewer.SetDefaultLights()

        # viewer.DisplayPrivilegedPlane(True, 1)
        # view.SetShadingModel(
        #        Graphic3d_TypeOfShadingModel.Graphic3d_TOSM_FRAGMENT)

        # background gradient
        with self.redraw_blocked():
            self.set_background_gradient(d.background_gradient)
            self.set_draw_boundaries(d.draw_boundaries)
            self.set_trihedron_mode(d.trihedron_mode)
            self.set_display_mode(d.display_mode)
            self.set_hidden_line_removal(d.hidden_line_removal)
            self.set_show_hidden_lines(d.show_hidden_lines)
            self.set_selection_mode(d.selection_mode)
            self.set_view_mode(d.view_mode)
            self.set_view_projection(d.view_projection)
            self.set_lock_rotation(d.lock_rotation)
            self.set_lock_zoom(d.lock_zoom)
            self.set_shape_color(d.shape_color)
            self.set_line_aspects(d.line_aspects)
            self.set_chordial_deviation(d.chordial_deviation)
            self._update_rendering_params()
            self.set_grid_mode(d.grid_mode)
            self.set_grid_colors(d.grid_colors)
            self.init_signals()

        self.redraw()

        qt_app = self._qt_app
        for child in self.children():
            self.child_added(child)
            qt_app.processEvents()

    def dump_gl_info(self):
        # Debug info
        try:
            ctx = self.graphics_driver.GetSharedContext()
            if ctx is None or not ctx.IsValid():
                return
            v1 = ctx.VersionMajor()
            v2 = ctx.VersionMinor()
            log.info("OpenGL version: {}.{}".format(v1, v2))
            log.info("GPU memory: {}".format(ctx.AvailableMemory()))
            log.info("GPU memory info: {}".format(ctx.MemoryInfo().ToCString()))

            msaa = self.msaa_samples = ctx.MaxMsaaSamples()
            log.info("Max MSAA samples: {}".format(msaa))

            supports_raytracing = ctx.HasRayTracing()
            log.info("Supports ray tracing: {}".format(supports_raytracing))
            if supports_raytracing:
                log.info("Supports textures: {}".format(ctx.HasRayTracingTextures()))
                log.info(
                    "Supports adaptive sampling: {}".format(
                        ctx.HasRayTracingAdaptiveSampling()
                    )
                )
                log.info(
                    "Supports adaptive sampling atomic: {}".format(
                        ctx.HasRayTracingAdaptiveSamplingAtomic()
                    )
                )
            else:
                ver_too_low = ctx.IsGlGreaterEqual(3, 1)
                if not ver_too_low:
                    log.info("OpenGL version must be >= 3.1")
                else:
                    ext = "GL_ARB_texture_buffer_object_rgb32"
                    if not ctx.CheckExtension(ext):
                        log.info("OpenGL extension {} is missing".format(ext))
                    else:
                        log.info("OpenGL glBlitFramebuffer is missing")
        except Exception as e:
            log.exception(e)

    def init_signals(self):
        d = self.declaration
        callbacks = self.widget._callbacks
        for name in callbacks.keys():
            cb = getattr(d, name, None)
            if cb is not None:
                callbacks[name].append(cb)

    def child_added(self, child):
        if isinstance(child, OccShape):
            self.add_shape_to_display(child)
        elif isinstance(child, OccDimension):
            self.add_dimension_to_display(child)
        else:
            super().child_added(child)

    def child_removed(self, child):
        if isinstance(child, OccShape):
            self.remove_shape_from_display(child)
        elif isinstance(child, OccDimension):
            self.remove_dimension_from_display(child)
        else:
            super().child_removed(child)

    def add_shape_to_display(self, occ_shape: OccShape):
        """Add an OccShape to the display"""
        d = occ_shape.declaration
        if not d.display:
            return
        displayed_shapes = self._displayed_shapes
        display = self.ais_context.Display
        qt_app = self._qt_app
        occ_shape.displayed = True
        for s in occ_shape.walk_shapes():
            # print(f'viewer added {s.declaration} parent={s.parent()}')
            # s.observe('ais_shape', self.on_ais_shape_changed)
            ais_shape = s.ais_shape
            if ais_shape is not None:
                try:
                    s.displayed = True
                    display(ais_shape, False)
                    displayed_shapes[s.shape] = s
                except RuntimeError as e:
                    log.exception(e)

                # Displaying can take a lot of time
                qt_app.processEvents()

        if isinstance(occ_shape, OccPart):
            d.rendered()
            for d in occ_shape.declaration.traverse():
                proxy = getattr(d, "proxy", None)
                if proxy is None:
                    continue
                if isinstance(proxy, OccPart):
                    d.rendered()
                if isinstance(proxy, OccDimension):
                    self.add_dimension_to_display(proxy)
                elif isinstance(proxy, OccDisplayItem):
                    self.add_item_to_display(proxy)

        self._redisplay_timer.start()

    def remove_shape_from_display(self, occ_shape: OccShape):
        displayed_shapes = self._displayed_shapes
        remove = self.ais_context.Remove
        occ_shape.displayed = False
        for s in occ_shape.walk_shapes(ignore_display=True):
            s.displayed = False
            # s.unobserve('ais_shape', self.on_ais_shape_changed)
            if s.get_member("ais_shape").get_slot(s) is None:
                continue  # Do not trigger creation
            ais_shape = s.ais_shape
            if ais_shape is not None:
                displayed_shapes.pop(s.shape, None)
                remove(ais_shape, False)

        if isinstance(occ_shape, OccPart):
            if occ_shape.get_member("ais_shape").get_slot(occ_shape) is not None:
                remove(occ_shape.ais_shape, False)

            for d in occ_shape.declaration.traverse():
                proxy = getattr(d, "proxy", None)
                if proxy is None:
                    continue
                if isinstance(proxy, OccDimension):
                    self.remove_dimension_from_display(proxy)
                elif isinstance(proxy, OccDisplayItem):
                    self.remove_item_from_display(proxy)

        self._redisplay_timer.start()

    def on_ais_shape_changed(self, change: dict[str, Any]):
        """Handle updates to the shape. This occurs when parts
        add or remove shapes (which may occur during animations).

        """
        if change["type"] != "update":
            return
        occ_shape = change["owner"]
        old_ais_shape = change["oldvalue"]
        if old_ais_shape is not None:
            self.remove_shape_from_display(occ_shape)
        new_ais_shape = change["value"]
        if new_ais_shape is not None:
            self.add_shape_to_display(occ_shape)
        self._redisplay_timer.start()

    def add_dimension_to_display(self, occ_dim: OccDimension):
        ais_dimension = occ_dim.dimension
        if ais_dimension is not None:
            self.ais_context.Display(ais_dimension, False)
            self._displayed_dimensions[ais_dimension] = occ_dim
        self._redisplay_timer.start()

    def remove_dimension_from_display(self, occ_dim: OccDimension):
        ais_dimension = occ_dim.dimension
        if ais_dimension is not None:
            self.ais_context.Remove(ais_dimension, False)
            self._displayed_dimensions.pop(ais_dimension, None)
        self._redisplay_timer.start()

    def add_item_to_display(self, occ_disp_item: OccDisplayItem):
        ais_object = occ_disp_item.item
        if ais_object is not None:
            self.ais_context.Display(ais_object, False)
            self._displayed_graphics[ais_object] = occ_disp_item
        self._redisplay_timer.start()

    def remove_item_from_display(self, occ_disp_item: OccDisplayItem):
        ais_object = occ_disp_item.item
        if ais_object is not None:
            self.ais_context.Remove(ais_object, False)
            self._displayed_graphics.pop(ais_object, None)
        self._redisplay_timer.start()

    def on_redisplay_requested(self):
        d = self.declaration
        self.ais_context.UpdateCurrentViewer()

        # Recompute bounding box
        bbox = self.get_bounding_box(self._displayed_shapes.keys())
        d.bbox = BBox(*bbox)

        # Trigger loaded
        d.rendered()

    # -------------------------------------------------------------------------
    # Viewer API
    # -------------------------------------------------------------------------
    def get_bounding_box(
        self, shapes: list[TopoDS_Shape]
    ) -> tuple[float, float, float, float, float, float]:
        """Compute the bounding box for the given list of shapes.
        Return values are in 3d coordinate space.

        Parameters
        ----------
        shapes: List
            A list of TopoDS_Shape to compute a bbox for

        Returns
        -------
        bbox: Tuple
            A tuple of (xmin, ymin, zmin, xmax, ymax, zmax).

        """
        bbox = Bnd_Box()
        for shape in shapes:
            BRepBndLib.Add_(shape, bbox)
        try:
            pmin = bbox.CornerMin()
            pmax = bbox.CornerMax()
        except RuntimeError:
            return (0, 0, 0, 0, 0, 0)
        return (pmin.X(), pmin.Y(), pmin.Z(), pmax.X(), pmax.Y(), pmax.Z())

    def get_screen_coordinate(self, point):
        """Convert a 3d coordinate to a 2d screen coordinate

        Parameters
        ----------
        (x, y, z): Tuple
            A 3d coordinate
        """
        return self.v3d_view.Convert(point[0], point[1], point[2], 0, 0)

    # -------------------------------------------------------------------------
    # Rendering parameters
    # -------------------------------------------------------------------------
    def set_chordial_deviation(self, deviation):
        # Turn up tesselation defaults
        self.prs3d_drawer.SetMaximalChordialDeviation(deviation)

    def set_lights(self, lights):
        viewer = self.v3d_viewer
        new_lights = []

        for d in lights:
            color, _ = color_to_quantity_color(d.color)
            if d.type == "directional":
                if "_" in d.orientation:
                    attr = "V3d_TypeOfOrientation_{}".format(d.orientation)
                else:
                    attr = "V3d_{}".format(d.orientation)
                orientation = getattr(V3d_TypeOfOrientation, attr, V3d.V3d_Zneg)
                light = V3d_DirectionalLight(orientation, color, d.headlight)
            elif d.type == "spot":
                light = V3d_SpotLight(d.position, d.direction, color)
                light.SetAngle(d.angle)
            else:
                light = V3d_AmbientLight(color)
            light.SetIntensity(d.intensity)

            if d.range:
                light.SetRange(d.range)

            viewer.AddLight(light)
            if d.enabled:
                viewer.SetLightOn(light)
            new_lights.append(light)

        for light in self.lights:
            viewer.DelLight(light)

        self.lights = new_lights

    def set_draw_boundaries(self, enabled: bool):
        self.prs3d_drawer.SetFaceBoundaryDraw(enabled)

    def set_hidden_line_removal(self, enabled: bool):
        view = self.v3d_view
        view.SetComputedMode(enabled)
        self.redraw()

    def set_show_hidden_lines(self, enabled: bool):
        drawer = self.prs3d_drawer
        if enabled:
            drawer.EnableDrawHiddenLine()
        else:
            drawer.DisableDrawHiddenLine()

    def set_antialiasing(self, enabled: bool):
        self._update_rendering_params()

    def set_shadows(self, enabled: bool):
        self._update_rendering_params()

    def set_reflections(self, enabled: bool):
        self._update_rendering_params()

    def set_raytracing(self, enabled: bool):
        self._update_rendering_params()

    def set_raytracing_depth(self, depth: int):
        self._update_rendering_params()

    def _update_rendering_params(self, **params):
        """Set the rendering parameters of the view

        Parameters
        ----------
        **params:
            See Graphic3d_RenderingParams members

        """
        d = self.declaration
        view = self.v3d_view
        rendering_params = view.ChangeRenderingParams()
        if d.raytracing:
            method = Graphic3d_RM_RAYTRACING
            view.SetShadingModel(Graphic3d_TypeOfShadingModel.Graphic3d_TOSM_PBR)
        else:
            method = Graphic3d_RM_RASTERIZATION
            view.SetShadingModel(Graphic3d_TypeOfShadingModel.Graphic3d_TOSM_FRAGMENT)

        defaults = dict(
            Method=method,
            RaytracingDepth=d.raytracing_depth,
            IsGlobalIlluminationEnabled=not d.raytracing,
            IsShadowEnabled=d.shadows,
            IsReflectionEnabled=d.reflections,
            IsAntialiasingEnabled=d.antialiasing,
            IsTransparentShadowEnabled=d.shadows,
            NbMsaaSamples=self.msaa_samples,
            NbRayTracingTiles=128,
            StereoMode=Graphic3d_StereoMode_QuadBuffer,
            AnaglyphFilter=Graphic3d_RenderingParams.Anaglyph_RedCyan_Optimized,
            ToReverseStereo=False,
        )
        defaults.update(**params)
        for attr, v in defaults.items():
            setattr(rendering_params, attr, v)

        self.redraw()

    def set_background_gradient(self, gradient):
        """Set the background gradient

        Parameters
        ----------
        gradient: Tuple
            Gradient parameters Color 1, Color 2, and optionally th fill method

        """
        c1, _ = color_to_quantity_color(gradient[0])
        c2, _ = color_to_quantity_color(gradient[1])
        fill_method = Aspect_GFM_VER
        if len(gradient) == 3:
            attr = "Aspect_GFM_{}".format(gradient[2].upper())
            fill_method = getattr(Aspect, attr, Aspect_GFM_VER)
        self.v3d_view.SetBgGradientColors(c1, c2, fill_method, True)

    def set_shape_color(self, color: Color):
        c, a = color_to_quantity_color(color)
        drawer = self.prs3d_drawer
        aspect = drawer.ShadingAspect()
        material = aspect.Material()
        material.SetColor(c)
        aspect.SetMaterial(material)
        aspect.SetColor(c)
        drawer.SetShadingAspect(aspect)

    def set_line_aspects(
        self,
        line_aspects: list[LineAspect],
    ):
        """Set the default line aspect for the drawer with the given name.
        Parameters
        ----------
        name: str
            The aspect name. Must be one of Line, Wire, SeenLine,
            HiddenLine, FreeBoundary, UnFreeBoundary, FaceBoundary
        color: Color
            The color to set
        width: float
            The line width
        line_type: str
            Must be one of (EMPTY, SOLID, DASH, DOT, DOTDASH)

        """
        drawer = self.prs3d_drawer
        for line_aspect in line_aspects:
            c, a = color_to_quantity_color(line_aspect.color)
            aspect_type = f"{line_aspect.aspect}Aspect"
            aspect = getattr(drawer, aspect_type)()
            aspect.SetColor(c)
            aspect.SetWidth(line_aspect.width)
            type_of_line = f"Aspect_TOL_{line_aspect.line_type.upper()}"
            aspect.SetTypeOfLine(getattr(Aspect, type_of_line))
            setter = getattr(drawer, f"Set{aspect_type}")
            setter(aspect)

    def set_trihedron_mode(self, mode: str):
        attr = "Aspect_TOTP_{}".format(mode.upper().replace("-", "_"))
        position = getattr(Aspect, attr)
        self.v3d_view.TriedronDisplay(position, BLACK, 0.1, V3d.V3d_ZBUFFER)
        self.redraw()

    def set_grid_mode(self, mode: str):
        if not mode:
            self.v3d_viewer.DeactivateGrid()
        else:
            a, b = mode.title().split("-")
            grid_type = getattr(Aspect_GridType, f"Aspect_GT_{a}")
            grid_mode = getattr(Aspect_GridDrawMode, f"Aspect_GDM_{b}")
            self.v3d_viewer.ActivateGrid(grid_type, grid_mode)

    def set_grid_colors(self, colors: tuple[Color, Color]):
        c1, _ = color_to_quantity_color(colors[0])
        c2, _ = color_to_quantity_color(colors[1])
        grid = self.v3d_viewer.Grid()
        grid.SetColors(c1, c2)

    def set_animations(self, enabled):
        self.animations = enabled

    # -------------------------------------------------------------------------
    # Viewer interaction
    # -------------------------------------------------------------------------
    def set_selection_mode(self, mode: str):
        """Set the selection mode.

        Parameters
        ----------
        mode: String
            The mode to use (Face, Edge, Vertex, Shell, or Solid)

        """
        ais_context = self.ais_context
        ais_context.Deactivate()
        if mode == "any":
            SelectionMode = AIS_Shape.SelectionMode_
            for mode in (
                TopAbs.TopAbs_SHAPE,
                TopAbs.TopAbs_SHELL,
                TopAbs.TopAbs_FACE,
                TopAbs.TopAbs_EDGE,
                TopAbs.TopAbs_WIRE,
                TopAbs.TopAbs_VERTEX,
            ):
                ais_context.Activate(SelectionMode(mode))
            return
        attr = "TopAbs_%s" % mode.upper()
        mode = getattr(TopAbs, attr, TopAbs.TopAbs_SHAPE)
        ais_context.Activate(AIS_Shape.SelectionMode_(mode))

    def set_display_mode(self, mode: str):
        v3d_mode = V3D_DISPLAY_MODES.get(mode)
        if v3d_mode is None:
            return
        self.ais_context.SetDisplayMode(v3d_mode, True)
        self.redraw()

    def set_display_units(self, units):
        pass

    def set_view_mode(self, mode: str):
        """Set the view mode or (or direction)

        Parameters
        ----------
        mode: String
            The mode to or direction to view.

        """
        proj_mode = V3D_VIEW_MODES.get(mode.lower())
        if proj_mode is None:
            return
        self.v3d_view.SetProj(proj_mode)

    def set_view_projection(self, mode: str):
        mode = getattr(Graphic3d_Camera, f"Projection_{mode.title()}")
        self.camera.SetProjectionType(mode)
        self.redraw()

    def set_lock_rotation(self, locked: bool):
        self.widget._lock_rotation = locked

    def set_lock_zoom(self, locked: bool):
        self.widget._lock_zoom = locked

    def zoom_factor(self, factor: float):
        self.v3d_view.SetZoom(factor)

    def rotate_view(self, x: float = 0, y: float = 0, z: float = 0):
        self.v3d_view.Rotate(x, y, z, True)

    def turn_view(self, x: float = 0, y: float = 0, z: float = 0):
        self.v3d_view.Turn(x, y, z, True)

    def fit_all(self):
        view = self.v3d_view
        view.FitAll()
        view.ZFitAll()
        self.redraw()

    def fit_selection(self):
        if not self._selected_shapes:
            return

        # Compute bounding box of the selection
        view = self.v3d_view
        pad = 20
        bbox = self.get_bounding_box(self._selected_shapes)
        xmin, ymin = self.get_screen_coordinate(bbox[0:3])
        xmax, ymax = self.get_screen_coordinate(bbox[3:6])
        cx, cy = int(xmin + (xmax - xmin) / 2), int(ymin + (ymax - ymin) / 2)
        self.ais_context.MoveTo(cx, cy, view, True)
        view.WindowFit(xmin - pad, ymin - pad, xmax + pad, ymax + pad)

    def take_screenshot(self, filename: str) -> bool:
        return self.v3d_view.Dump(filename)

    # -------------------------------------------------------------------------
    # Display Handling
    # -------------------------------------------------------------------------
    def view_stats(self) -> str:
        """Get view stats information

        Returns
        -------
        stats: String
            The formatted stat string

        Example
        -------
        FPS:          0.2 (0.9)
        CPU FPS:      5.5 (13.4)
        Layers:         5
        Structs:        4
        Rendered          (imm.)
            Layers:     3 (2)
        Structs:     4 (2)

        """
        return self.view.StatisticInformation().ToCString()

    def clear_selection(self):
        """Clear selection"""
        self.ais_context.ClearSelected(True)

    def update_selection(
        self,
        pos: Optional[tuple[float, float]],
        area: Optional[tuple[float, float, float, float]],
        shift: bool,
    ):
        """Update the selection state"""
        view = self.v3d_view
        ais_context = self.ais_context

        if area:
            xmin, ymin, dx, dy = area
            ais_context.Select(xmin, ymin, xmin + dx, ymin + dy, view, True)
        elif shift:
            # multiple select if shift is pressed
            ais_context.ShiftSelect(True)
        else:
            ais_context.Select(True)
        ais_context.InitSelected()

        # Lookup the shape declrations based on the selection context
        selection: dict[Shape, SelectionInfoType] = {}
        shapes: list[TopoDS_Shape] = []
        occ_shapes = {s.ais_shape: s for s in self._displayed_shapes.values()}
        while ais_context.MoreSelected():
            ais_object = ais_context.SelectedInteractive()
            occ_shape = occ_shapes.get(ais_object)
            if occ_shape is not None:
                d = occ_shape.declaration
                topods_shape = ais_context.SelectedShape()
                if isinstance(ais_object, MeshVS_Mesh):
                    mesh_info: SelectionInfoType = selection.get(d, {})
                    if d not in selection:
                        selection[d] = mesh_info
                    # Mesh selection works differently...
                    ais_selection = ais_context.Selection()
                    owner = ais_selection.Value()

                    if isinstance(owner, MeshVS_MeshEntityOwner):
                        item_type = owner.Type()
                        i = owner.ID()
                        attr = str(item_type).split("_")[-1].lower() + "s"
                        selection_info = mesh_info.get(attr)
                        if selection_info is None:
                            selection_info = mesh_info[attr] = {}
                        item_iter = getattr(d.topology, attr, None)
                        if item_iter is not None:
                            selection_info[i] = item_iter[i]
                    else:
                        mesh_info["meshs"] = {0: occ_shape}
                    del mesh_info
                elif not topods_shape.IsNull():
                    # Try to lookup index based on topology
                    shape_type = topods_shape.ShapeType()
                    attr = str(shape_type).split("_")[-1].lower() + "s"
                    if attr == "vertexs":
                        shape_list = occ_shape.topology.vertices
                    else:
                        shape_list = getattr(occ_shape.topology, attr, ())

                    # Lookup index
                    # TODO: Better way to do this?
                    i = 0
                    for i, s in enumerate(shape_list):
                        if topods_shape.IsPartner(s):
                            break
                    shapes.append(topods_shape)
                    # Insert what was selected into the options
                    shape_info: SelectionInfoType = selection.get(d, {})
                    if d not in selection:
                        selection[d] = shape_info
                    selection_info = shape_info.get(attr)
                    if selection_info is None:
                        selection_info = shape_info[attr] = {}
                    selection_info[i] = topods_shape
                    del shape_info

                # Mark it as found we don't know what shape it's from
                # if not found:
                #    if None not in selection:
                #        selection[None] = {}
                #    if attr not in selection[None]:
                #        selection[None][attr] = {}
                #    info = selection[None][attr]
                #    # Just keep incrementing the index
                #    info[len(info)] = topods_shape
            ais_context.NextSelected()

        if shift:
            ais_context.UpdateSelected(True)
        # Set selection
        self._selected_shapes = shapes
        self.declaration.selection = ViewerSelection(
            selection=selection, position=pos, area=area
        )

    def update_display(self, change=None):
        """Queue an update request"""
        self._redisplay_timer.start()

    def clear_display(self):
        """Remove all shapes and dimensions drawn"""
        # Erase all just hides them
        remove = self.ais_context.Remove
        for occ_shape in self._displayed_shapes.values():
            remove(occ_shape.ais_shape, False)
        for ais_dim in self._displayed_dimensions.keys():
            remove(ais_dim, False)
        for ais_item in self._displayed_graphics.keys():
            remove(ais_item, False)
        self.gfx_structure.Clear()
        self.ais_context.UpdateCurrentViewer()

    def reset_view(self):
        """Reset to default zoom and orientation"""
        self.v3d_view.Reset()

    @contextmanager
    def redraw_blocked(self):
        """Temporarily stop redraw during"""
        self._redraw_blocked = True
        yield
        self._redraw_blocked = False

    def redraw(self):
        if not self._redraw_blocked:
            self.v3d_view.Redraw()

    def update(self):
        """Redisplay"""
        self.ais_context.UpdateCurrentViewer()
