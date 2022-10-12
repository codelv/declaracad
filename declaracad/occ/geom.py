"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 26, 2020

@author: jrm
"""
import math
import warnings
from contextlib import contextmanager
from typing import Any, Optional, Union

from atom.api import Atom, Float, Property, Typed
from OCCT.BRep import BRep_Tool
from OCCT.Geom import Geom_Line
from OCCT.gp import gp, gp_Ax1, gp_Dir, gp_Pnt, gp_Vec
from OCCT.TopoDS import TopoDS_Shape

try:
    from SMESH.SMDS import SMDS_MeshNode
except ImportError as e:
    warnings.warn(f"{e}")

    class SMDS_MeshNode:  # type: ignore
        pass


class Settings(Atom):
    """Used to manage tolerance settings"""

    tolerance = Float(1e-6)


settings = Settings()


@contextmanager
def tolerance(tol: float):
    _tol = settings.tolerance
    settings.tolerance = tol
    yield tol
    settings.tolerance = _tol


class BBox(Atom):
    xmin = Float()
    ymin = Float()
    zmin = Float()
    xmax = Float()
    ymax = Float()
    zmax = Float()

    def _get_dx(self) -> float:
        return self.xmax - self.xmin

    dx = Property(_get_dx, cached=True)

    def _get_dy(self) -> float:
        return self.ymax - self.ymin

    dy = Property(_get_dy, cached=True)

    def _get_dz(self) -> float:
        return self.zmax - self.zmin

    dz = Property(_get_dz, cached=True)

    def __init__(
        self,
        xmin: float = 0,
        ymin: float = 0,
        zmin: float = 0,
        xmax: float = 0,
        ymax: float = 0,
        zmax: float = 0,
    ):
        super(BBox, self).__init__(
            xmin=xmin, ymin=ymin, zmin=zmin, xmax=xmax, ymax=ymax, zmax=zmax
        )

    def __getitem__(self, key) -> Union[tuple, float]:
        return (self.xmin, self.ymin, self.zmin, self.xmax, self.ymax, self.zmax)[key]

    def _get_center(self) -> "Point":
        return Point(
            (self.xmin + self.xmax) / 2,
            (self.ymin + self.ymax) / 2,
            (self.zmin + self.zmax) / 2,
        )

    center = Property(_get_center, cached=True)

    def _get_diagonal(self) -> float:
        return math.sqrt(self.dx**2 + self.dy**2 + self.dz**2)

    diagonal = Property(_get_diagonal, cached=True)

    def _get_min(self) -> "Point":
        return Point(self.xmin, self.ymin, self.zmin)

    def _get_max(self) -> "Point":
        return Point(self.xmax, self.ymax, self.zmax)

    min = Property(_get_min)
    max = Property(_get_max)

    def __repr__(self) -> str:
        return "<BBox: x=%s y=%s z=%s w=%s h=%s d=%s>" % (
            self.xmin,
            self.ymin,
            self.zmin,
            self.dx,
            self.dy,
            self.dz,
        )


class Point(Atom):
    proxy = Typed(gp_Pnt)

    x = Float(0, strict=False)
    y = Float(0, strict=False)
    z = Float(0, strict=False)

    def __init__(self, x=0, y=0, z=0, **kwargs):
        if isinstance(x, TopoDS_Shape):
            pnt = BRep_Tool.Pnt_(x)
            x, y, z = pnt.X(), pnt.Y(), pnt.Z()
        elif isinstance(x, (gp_Pnt, gp_Dir, gp_Vec, SMDS_MeshNode)):
            x, y, z = x.X(), x.Y(), x.Z()
        super().__init__(x=x, y=y, z=z, **kwargs)

    def _default_proxy(self) -> gp_Pnt:
        return gp_Pnt(self.x, self.y, self.z)

    # ========================================================================
    # Binds changes to the proxy
    # ========================================================================
    def _observe_x(self, change):
        if change["type"] == "update":
            self.proxy.SetX(self.x)

    def _observe_y(self, change):
        if change["type"] == "update":
            self.proxy.SetY(self.y)

    def _observe_z(self, change):
        if change["type"] == "update":
            self.proxy.SetZ(self.z)

    # ========================================================================
    # Slice support
    # ========================================================================
    def __getitem__(self, key):
        return (self.x, self.y, self.z).__getitem__(key)

    def __setitem__(self, key, value):
        p = [self.x, self.y, self.z]
        p[key] = value
        self.x, self.y, self.z = p

    # ========================================================================
    # Operations support
    # ========================================================================
    def __add__(self, other):
        p = self.__coerce__(other)
        return self.__class__(self.x + p.x, self.y + p.y, self.z + p.z)

    def __sub__(self, other):
        p = self.__coerce__(other)
        return self.__class__(self.x - p.x, self.y - p.y, self.z - p.z)

    def __eq__(self, other):
        return self.is_equal(other)

    def is_equal(self, other, tol=None):
        p = self.__coerce__(other)
        return self.proxy.IsEqual(p.proxy, tol or settings.tolerance)

    def __mul__(self, other):
        return self.__class__(self.x * other, self.y * other, self.z * other)

    def __truediv__(self, other):
        return self.__class__(self.x / other, self.y / other, self.z / other)

    def cross(self, other) -> "Point":
        p = self.__coerce__(other)
        return self.__coerce__(self.proxy.Crossed(p.proxy))

    def dot(self, other) -> float:
        p = self.__coerce__(other)
        return self.proxy.Dot(p.proxy)

    def midpoint(self, other) -> "Point":
        p = self.__coerce__(other)
        return self.__class__(
            (self.x + p.x) / 2, (self.y + p.y) / 2, (self.z + p.z) / 2
        )

    def distance(self, other) -> float:
        p = self.__coerce__(other)
        return self.proxy.Distance(p.proxy)

    def angle(self, other) -> float:
        """Returns the angle value between 0 and pi in radians"""
        v = gp_Vec(self.__coerce__(other).proxy.XYZ())
        return gp_Vec(self.proxy.XYZ()).Angle(v)

    def angle_with_ref(self, other, ref) -> float:
        """Computes the angle, in radians, between this vector and vector ref.
        The result is a value between -pi and pi.
        """
        ref = gp_Vec(self.__coerce__(ref).proxy.XYZ())
        v = gp_Vec(self.__coerce__(other).proxy.XYZ())
        return gp_Vec(self.proxy.XYZ()).AngleWithRef(v, ref)

    def angle2d(self, other) -> float:
        """Angle between the x and y components
        Returns the angle value between 0 and pi in radians
        """
        p = self.__coerce__(other)
        v = gp_Vec(p.x, p.y, 0)
        return gp_Vec(self.x, self.y, 0).Angle(v)

    def magnitude(self) -> float:
        return self.proxy.Distance(gp_Pnt())

    def distance2d(self, other) -> float:
        p = self.__coerce__(other)
        return math.sqrt((self.x - p.x) ** 2 + (self.y - p.y) ** 2)

    def replace(self, **kwargs) -> "Point":
        """Create a copy with the value replaced with the given parameters."""
        p = Point(*self[:])
        for k, v in kwargs.items():
            setattr(p, k, v)
        return p

    def offset(self, distance: float, direction: "Direction") -> "Point":
        """Create a point offset by distance in the given direction

        Parameters
        ----------
        distance: float
            The offset distance
        direction: Union[Tuple[float, ...], Direction, gp_Dir]
            The direction to offset. Will be coerced

        Returns
        -------
        p: Point
            Point offset from this point

        """
        # Use proxy to so it is normalized
        d = coerce_direction(direction).proxy
        return Point(Geom_Line(self.proxy, d).Value(distance))

    def __hash__(self):
        return hash(self[:])

    @classmethod
    def __coerce__(self, other):
        return coerce_point(other)

    def __str__(self):
        return str((round(self.x, 6), round(self.y, 6), round(self.z, 6)))

    def __repr__(self):
        return "<Point: x=%s y=%s z=%s>" % self[:]


class Direction(Point):
    proxy = Typed(gp_Dir)

    def _default_proxy(self):
        return gp_Dir(self.x, self.y, self.z)

    @classmethod
    def __coerce__(self, other) -> "Direction":
        return coerce_direction(other)

    def __repr__(self) -> str:
        return "<Direction: x=%s y=%s z=%s>" % self[:]

    def __neg__(self) -> "Direction":
        return self.reversed()

    def reversed(self) -> "Direction":
        """Return a reversed copy"""
        v = self.proxy.Reversed()
        return Direction(v.X(), v.Y(), v.Z())

    def rotated(
        self, angle: float, axis: Optional[tuple[Point, "Direction"]] = None
    ) -> "Direction":
        """Rotate by angle radians about the given axis. The axis defaults
        to the origin and z direction.

        """
        axis = gp_Ax1(axis[0].proxy, axis[1].proxy) if axis else gp.OZ_()
        v = self.proxy.Rotated(axis, angle)
        return Direction(v.X(), v.Y(), v.Z())

    @classmethod
    def XY(cls, x: float, y: float) -> "Direction":
        # Create a direction in the 2d XY plane with Z normal
        v = gp.DZ_().Rotated(gp.OZ_(), math.atan2(y, x))
        return Direction(v.X(), v.Y(), v.Z())

    @classmethod
    def XZ(cls, x: float, y: float) -> "Direction":
        # Create a direction in the XY plane
        v = gp_Dir()
        v.Rotate(gp.OY_(), math.atan2(y, x))
        return Direction(v.X(), v.Y(), v.Z())

    @classmethod
    def YZ(cls, x: float, y: float) -> "Direction":
        # Create a direction in the XY plane
        v = gp_Dir()
        v.Rotate(gp.OX_(), math.atan2(y, x))
        return Direction(v.X(), v.Y(), v.Z())

    def is_parallel(self, other, tol: Optional[float] = None) -> bool:
        p = self.__coerce__(other)
        return self.proxy.IsParallel(p.proxy, tol or settings.tolerance)

    def is_opposite(self, other, tol: Optional[float] = None) -> bool:
        p = self.__coerce__(other)
        return self.proxy.IsOpposite(p.proxy, tol or settings.tolerance)

    def is_normal(self, other, tol: Optional[float] = None) -> bool:
        """Check if perpendicular"""
        p = self.__coerce__(other)
        return self.proxy.IsNormal(p.proxy, tol or settings.tolerance)


def coerce_point(arg: Any) -> Point:
    if isinstance(arg, TopoDS_Shape):
        arg = BRep_Tool.Pnt_(arg)
    if hasattr(arg, "XYZ"):  # copy from gp_Pnt, gp_Vec, gp_Dir, etc..
        return Point(arg.X(), arg.Y(), arg.Z())
    if isinstance(arg, Point):
        return arg
    if isinstance(arg, dict):
        return Point(**arg)
    return Point(*arg)


def coerce_direction(arg: Any) -> Direction:
    if isinstance(arg, TopoDS_Shape):
        arg = BRep_Tool.Pnt_(arg)
    if hasattr(arg, "XYZ"):  # copy from gp_Pnt2d, gp_Vec2d, gp_Dir2d, etc..
        return Direction(arg.X(), arg.Y(), arg.Z())
    if isinstance(arg, Direction):
        return arg
    if isinstance(arg, dict):
        return Direction(**arg)
    return Direction(*arg)


def coerce_rotation(arg: Union[float, int, tuple[float, float]]) -> float:
    if isinstance(arg, (int, float)):
        return float(arg)
    return float(math.atan2(*arg))
