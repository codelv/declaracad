"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on March 25, 2020

@author: jrm
"""
from atom.api import Typed
from OCCT.PrsDim import (
    PrsDim_AngleDimension, PrsDim_DiameterDimension, PrsDim_LengthDimension,
    PrsDim_RadiusDimension, PrsDim_Dimension
)
from OCCT.BRep import BRep_Tool
from OCCT.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
from OCCT.GC import GC_MakePlane
from OCCT.gp import gp_Pnt, gp_Dir
from OCCT.TCollection import TCollection_AsciiString
from OCCT.TopoDS import TopoDS, TopoDS_Edge, TopoDS_Vertex, TopoDS_Shape
from OCCT.TopAbs import TopAbs_ShapeEnum

from ..dimension import (
    ProxyDimension, ProxyAngleDimension, ProxyDiameterDimension,
    ProxyRadiusDimension, ProxyLengthDimension
)
from ..shape import Point

from .occ_shape import Topology

from declaracad.core.utils import log

from .utils import color_to_quantity_color


class OccDimension(ProxyDimension):
    #: A reference to the toolkit dimension created by the proxy.
    dimension = Typed(PrsDim_Dimension)

    # -------------------------------------------------------------------------
    # Initialization API
    # -------------------------------------------------------------------------
    def create_dimension(self):
        pass

    def init_dimension(self):
        d = self.declaration
        dim = self.dimension
        if dim is None:
            return
        if d.flyout:
            dim.SetFlyout(d.flyout)
        if d.units:
            dim.SetDisplayUnits(TCollection_AsciiString(d.units))

        aspect = dim.DimensionAspect()
        if d.color:
            color, transparency = color_to_quantity_color(d.color)
            aspect.SetCommonColor(color)
        if d.arrow_tail_size:
            aspect.SetArrowTailSize(d.arrow_tail_size)
        if d.extension_size:
            aspect.SetExtensionSize(d.extension_size)
        if d.show_units:
            aspect.MakeUnitsDisplayed(d.show_units)
        dim.SetDimensionAspect(aspect)

    def update_dimension(self):
        """ Recreates the dimension catching any errors

        """
        try:
            self.create_dimension()
            self.init_dimension()
        except Exception as e:
            self.dimension = None
            log.exception(e)

    def activate_top_down(self):
        """ Activate the proxy for the top-down pass.

        """
        self.update_dimension()

    def activate_bottom_up(self):
        """ Activate the proxy tree for the bottom-up pass.

        """
        pass

    # -------------------------------------------------------------------------
    # Proxy API
    # -------------------------------------------------------------------------
    def set_units(self, units):
        self.update_dimension()

    def set_show_units(self, show_units):
        self.update_dimension()

    def set_shapes(self, shapes):
        self.update_dimension()

    def set_display(self, display):
        self.update_dimension()

    def set_color(self, color):
        self.update_dimension()

    def set_direction(self, direction):
        self.update_dimension()

    def set_flyout(self, flyout):
        self.update_dimension()

    def set_extension_size(self, size):
        self.update_dimension()

    def set_arrow_tail_size(self, size):
        self.update_dimension()

    # -------------------------------------------------------------------------
    # Utils
    # -------------------------------------------------------------------------
    def get_shapes(self):
        """ Get the shapes casted to the actual type """
        shapes = []
        for s in self.declaration.shapes:
            if isinstance(s, Point):
                shapes.append(BRepBuilderAPI_MakeVertex(s.proxy).Vertex())
            else:
                shapes.append(Topology.cast_shape(s))

        return shapes

    def make_custom_plane(self, dimension):
        d = self.declaration
        pln = dimension.GetPlane()
        axis = pln.Axis()
        axis.SetDirection(gp_Dir(*d.direction))
        pln.SetAxis(axis)
        return pln


class OccAngleDimension(OccDimension, ProxyAngleDimension):
    #: A reference to the toolkit dimension created by the proxy.
    dimension = Typed(PrsDim_AngleDimension)

    def create_dimension(self):
        d = self.declaration
        self.dimension = PrsDim_AngleDimension(*self.get_shapes())


class OccLengthDimension(OccDimension, ProxyLengthDimension):
    #: A reference to the toolkit dimension created by the proxy.
    dimension = Typed(PrsDim_LengthDimension)

    def make_plane(self, v1, v2):
        d = self.declaration
        p1 = BRep_Tool.Pnt_(v1)
        p2 = BRep_Tool.Pnt_(v2)
        p3 = (d.direction + p2).proxy
        return GC_MakePlane(p1, p2, p3).Value().Pln()

    def create_dimension(self):
        d = self.declaration
        if not d.shapes:
            return
        args = self.get_shapes()
        s = args[0]
        if len(args) == 1:
            topo = Topology(shape=s)
            args.append(self.make_plane(*topo.vertices_from_edge(s)[0:]))
        elif isinstance(s, TopoDS_Vertex) and len(args) == 2:
            args.append(self.make_plane(s, args[1]))
        self.dimension = PrsDim_LengthDimension(*args)


class OccRadiusDimension(OccDimension, ProxyRadiusDimension):
    #: A reference to the toolkit dimension created by the proxy.
    dimension = Typed(PrsDim_RadiusDimension)

    def create_dimension(self):
        d = self.declaration
        self.dimension = PrsDim_RadiusDimension(*self.get_shapes())


class OccDiameterDimension(OccDimension, ProxyDiameterDimension):
    #: A reference to the toolkit dimension created by the proxy.
    dimension = Typed(PrsDim_DiameterDimension)

    def create_dimension(self):
        d = self.declaration
        self.dimension = PrsDim_DiameterDimension(*self.get_shapes())
