"""
Copyright (c) 2017-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 13, 2017

@author: jrm
"""
from enaml.core.api import Looper, Conditional, Include
from enaml.widgets.api import Timer
from .algo import (
    Cut,
    Common,
    Fuse,
    Split,
    Intersection,
    Sew,
    Fillet,
    Chamfer,
    Offset,
    OffsetShape,
    ThickSolid,
    Pipe,
    LinearForm,
    RevolutionForm,
    ThruSections,
    DraftAngle,
    Transform,
    Translate,
    Rotate,
    Scale,
    Mirror,
    NormalProjection,
    Extend,
)
from .dimension import (
    AngleDimension,
    DiameterDimension,
    LengthDimension,
    RadiusDimension,
)
from .draw import (
    Plane,
    Vertex,
    Edge,
    Line,
    Rectangle,
    Segment,
    Arc,
    Circle,
    Ellipse,
    Hyperbola,
    Parabola,
    Polyline,
    Polygon,
    BSpline,
    Bezier,
    Text,
    TrimmedCurve,
    Svg,
    Wire,
    MiddlePath,
    BSplineSurface,
)

from .shape import (
    Part,
    Point,
    Direction,
    BBox,
    Shape,
    RawShape,
    Face,
    Texture,
    Material,
    Box,
    Cylinder,
    Tube,
    Sphere,
    Cone,
    Wedge,
    Torus,
    HalfSpace,
    Prism,
    Revol,
    TopoShape,
    RawPart,
)
from .mesh import Mesh
from .impl.topology import Topology
from .loaders import load_model
from .display import DisplayLine, DisplayArrow, DisplayText, DisplayPlane
from .solver import Solver

Loft = ThruSections
Sweep = Pipe
Extrude = Prism
