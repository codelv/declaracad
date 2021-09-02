"""
Copyright (c) 2016-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 26, 2016

@author: jrm
"""
import math
from atom.api import (
   Atom, Event, List, Tuple, Bool, Int, Enum, Typed, ForwardTyped, observe,
   Coerced, Dict, Str, Float, Instance, FloatRange, set_default
)
from enaml.core.declarative import d_
from enaml.colors import Color, ColorMember, parse_color
from enaml.widgets.control import Control, ProxyControl

from declaracad.occ.shape import BBox, Point, Direction


def color_pair_coercer(arg):
    """ Coerce to a tuple of colors

    """
    if not isinstance(arg, (tuple, list)):
        c1, c2 = [arg, arg]
    else:
        c1, c2 = arg
    if not isinstance(c1, Color):
        c1 = parse_color(c1)
    if not isinstance(c2, Color):
        c2 = parse_color(c2)
    return (c1, c2)


class ViewerSelection(Atom):
    #: Selected shape or shapes
    selection = Dict()

    #: Selection position, may be None
    position = Instance(tuple)

    #: Selection area, may be None
    area = Instance(tuple)


class ViewerLight(Atom):
    """ A Light in the view

    """
    #: Whether the light is on
    enabled = Bool(True)

    #: Type of light
    type = Enum("directional", "spot", "ambient")

    #: Color of the light source
    color = ColorMember()

    #: Name of the light
    name = Str()

    #: Intensity of light source
    intensity = FloatRange(0.0, 1.0, 1.0)

    # ------------------------------------------------------------------------
    # Directional light parameters
    # ------------------------------------------------------------------------
    orientation = Enum(
        'XnegYnegZneg',
        'Xpos', 'Ypos', 'Zpos',
        'Xneg', 'Yneg', 'Zneg',
        'XposYpos', 'XposZpos', 'YposZpos',
        'XnegYneg', 'XnegYpos', 'XnegZneg',
        'XnegZpos', 'YnegZneg', 'YnegZpos',
        'XposYneg', 'XposZneg', 'YposZneg',
        'XposYposZpos', 'XposYnegZpos', 'XposYposZneg',
        'XnegYposZpos', 'XposYnegZneg', 'XnegYposZneg',
        'XnegYnegZpos',
        'Zup_AxoLeft', 'Zup_AxoRight',
        'Zup_Front', 'Zup_Back', 'Zup_Top', 'Zup_Bottom', 'Zup_Left',
        'Zup_Right', 'Yup_AxoLeft', 'Yup_AxoRight', 'Yup_Front', 'Yup_Back',
        'Yup_Top', 'Yup_Bottom', 'Yup_Left', 'Yup_Right')

    #: Headlight flag means that light position/direction are defined not in a
    #: World coordinate system, but relative to the camera orientation
    headlight = Bool()

    # ------------------------------------------------------------------------
    # Spot light parameters
    # ------------------------------------------------------------------------
    #: Position of the spot light
    position = Typed(Point)

    #: Direction of the spot light
    direction = Typed(Direction)

    def _default_direction(self):
        return Direction(-1, -1, -1)

    #: Range of the light source, 0.0 means infininte
    range = Float(0.0, strict=False)

    # Angle in radians of the cone created by the spot
    angle = FloatRange(0.0, math.pi, math.pi/2)


class ProxyOccViewer(ProxyControl):
    """ The abstract definition of a proxy Viewer object.
    """
    #: A reference to the Viewer declaration.
    declaration = ForwardTyped(lambda: OccViewer)

    def set_position(self, position):
        raise NotImplementedError

    def set_pan(self, position):
        raise NotImplementedError

    def set_chordial_deviation(self, deviation):
        raise NotImplementedError

    def set_lights(self, lights):
        raise NotImplementedError

    def set_background_gradient(self, gradient):
        raise NotImplementedError

    def set_shape_color(self, color):
        raise NotImplementedError

    def set_rotation(self, rotation):
        raise NotImplementedError

    def set_selection_mode(self, mode):
        raise NotImplementedError

    def set_selected(self, position):
        raise NotImplementedError

    def set_selected_area(self, area):
        raise NotImplementedError

    def set_double_buffer(self, enabled):
        raise NotImplementedError

    def set_display_mode(self, mode):
        raise NotImplementedError

    def set_trihedron_mode(self, mode):
        raise NotImplementedError

    def set_view_mode(self, mode):
        raise NotImplementedError

    def set_view_projection(self, mode):
        raise NotImplementedError

    def set_shadows(self, enabled):
        raise NotImplementedError

    def set_reflections(self, enabled):
        raise NotImplementedError

    def set_antialiasing(self, enabled):
        raise NotImplementedError

    def set_raytracing(self, enabled):
        raise NotImplementedError

    def set_raytracing_depth(self, depth):
        raise NotImplementedError

    def set_draw_boundaries(self, enabled):
        raise NotImplementedError

    def set_hidden_line_removal(self, enabled):
        raise NotImplementedError

    def set_grid_mode(self, mode):
        raise NotImplementedError

    def set_grid_colors(self, colors):
        raise NotImplementedError

    def set_lock_rotation(self, locked):
        raise NotImplementedError

    def set_lock_zoom(self, locked):
        raise NotImplementedError

    def set_animations(self, enabled):
        raise NotImplementedError

    def fit_all(self):
        raise NotImplementedError

    def fit_selection(self):
        raise NotImplementedError

    def clear_selection(self):
        raise NotImplementedError

    def take_screenshot(self, filename):
        raise NotImplementedError

    def zoom_factor(self, zoom):
        raise NotImplementedError

    def rotate_view(self, x=0, y=0, z=0):
        raise NotImplementedError

    def turn_view(self, x=0, y=0, z=0):
        raise NotImplementedError

    def reset_view(self):
        raise NotImplementedError

    def clear_display(self):
        raise NotImplementedError

    def update_display(self):
        raise NotImplementedError


class OccViewer(Control):
    """ A widget to view OpenCascade shapes.
    """
    #: A reference to the ProxySpinBox object.
    proxy = Typed(ProxyOccViewer)

    #: Bounding box of displayed shapes. A tuple of the following values
    #: (xmin, ymin, zmin, xmax, ymax, zmax).
    bbox = d_(Typed(BBox), writable=False)

    #: Any errors that occurred while rendering
    errors = d_(Dict(), writable=False)

    #: Display mode
    display_mode = d_(Enum('shaded', 'wireframe'))

    #: Selection mode
    selection_mode = d_(Enum(
        'any', 'shape', 'shell', 'face', 'edge', 'wire', 'vertex'))

    #: Selected items
    selection = d_(Typed(ViewerSelection), writable=False)

    #: View direction
    view_mode = d_(Enum('iso', 'top', 'bottom', 'left', 'right', 'front',
                        'rear'))

    #: View projection
    view_projection = d_(Enum('orthographic', 'perspective', 'stereo'))

    # -------------------------------------------------------------------------
    # Grid
    # -------------------------------------------------------------------------
    grid_mode = d_(Enum('', 'rectangular-lines', 'rectangular-points',
                        'circular-lines', 'circular-points'))
    grid_colors = d_(Coerced(tuple, coercer=color_pair_coercer))

    def _default_grid_colors(self):
        return (parse_color('#888'), parse_color('#444'))

    #: Show tahedron
    trihedron_mode = d_(Enum('right-lower', 'right-upper', 'left-lower',
                             'left-upper'))

    #: Background gradient this is corecred from a of strings
    background_gradient = d_(Coerced(tuple, coercer=color_pair_coercer))

    def _default_background_gradient(self):
        return (parse_color('white'), parse_color('silver'))

    #: Default shape rendering color if none is defined
    shape_color = d_(ColorMember('steelblue'))

    #: Display shadows
    shadows = d_(Bool(False))

    #: Display reflections
    reflections = d_(Bool(False))

    #: Enable antialiasing
    antialiasing = d_(Bool(True))

    #: Enable raytracing
    raytracing = d_(Bool(False))

    #: Raytracing depth
    raytracing_depth = d_(Int(3))

    #: Enable animations
    animations = d_(Bool(True))

    #: Enable hidden line removal
    hidden_line_removal = d_(Bool(False))

    #: Draw face boundaries
    draw_boundaries = d_(Bool(False))

    #: View expands freely in width by default.
    hug_width = set_default('ignore')

    #: View expands freely in height by default.
    hug_height = set_default('ignore')

    #: Lock rotation so the mouse cannot not rotate
    lock_rotation = d_(Bool())

    #: Lock zoom so the mouse wheel cannot not zoom
    lock_zoom = d_(Bool())

    #: Lights
    lights = d_(List(ViewerLight))

    def _default_lights(self):
        headlight = ViewerLight(
            type="directional", color="white", headlight=True)
        ambient = ViewerLight(type="ambient", color="white", intensity=0.95)
        return [headlight, ambient]

    #: Chordial Deviation. This is the "smoothness" of curves
    chordial_deviation = d_(Float(0.001, strict=False))

    #: Events
    #: Raise StopIteration to indicate handling should stop
    key_pressed = d_(Event(), writable=False)
    mouse_pressed = d_(Event(), writable=False)
    mouse_released = d_(Event(), writable=False)
    mouse_wheeled = d_(Event(), writable=False)
    mouse_moved = d_(Event(), writable=False)

    #: Loading status
    loading = d_(Bool(), writable=False)
    progress = d_(Float(strict=False), writable=False)

    # -------------------------------------------------------------------------
    # Observers
    # -------------------------------------------------------------------------
    @observe('position', 'display_mode', 'view_mode', 'trihedron_mode',
             'selection_mode', 'background_gradient', 'double_buffer',
             'shadows', 'reflections', 'antialiasing', 'lock_rotation',
             'lock_zoom', 'draw_boundaries', 'hidden_line_removal',
             'shape_color', 'raytracing_depth', 'lights', 'view_projection',
             'grid_mode', 'grid_colors', 'animations')
    def _update_proxy(self, change):
        """ An observer which sends state change to the proxy.
        """
        # The superclass handler implementation is sufficient.
        super(OccViewer, self)._update_proxy(change)

    # -------------------------------------------------------------------------
    # Viewer API
    # -------------------------------------------------------------------------
    def fit_all(self):
        """ Zoom in and center on all item(s) """
        self.proxy.fit_all()

    def fit_selection(self):
        """ Zoom in and center on the selected item(s) """
        self.proxy.fit_selection()

    def clear_selection(self):
        """ Clear selection """
        self.proxy.clear_selection()

    def take_screenshot(self, filename):
        """ Take a screenshot and save it with the given filename """
        self.proxy.take_screenshot(filename)

    def zoom_factor(self, factor):
        """ Zoom in by a given factor """
        self.proxy.zoom_factor(factor)

    def rotate_view(self, *args, **kwargs):
        """ Rotate by the given number of degrees about the current axis"""
        self.proxy.rotate_view(*args, **kwargs)

    def turn_view(self, *args, **kwargs):
        """ Rotate by the given number of degrees about the current axis"""
        self.proxy.turn_view(*args, **kwargs)

    def reset_view(self):
        """ Reset zoom to defaults """
        self.proxy.reset_view()

    def clear_display(self):
        """ Clear the display, all children should be removed before calling
        this or they'll be rerendered.
        """
        self.proxy.clear_display()

    def update_display(self):
        """ Trigger an update of the display """
        self.proxy.update_display()
