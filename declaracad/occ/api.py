"""
Copyright (c) 2017-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 13, 2017

@author: jrm
"""
from enaml.core.api import Conditional, Include, Looper
from enaml.widgets.api import Timer

from .algo import (
    Chamfer,
    Common,
    Cut,
    DraftAngle,
    Extend,
    Fillet,
    Fuse,
    Intersection,
    LinearForm,
    Mirror,
    NormalProjection,
    Offset,
    OffsetShape,
    Pipe,
    RevolutionForm,
    Rotate,
    Scale,
    Sew,
    Split,
    ThickSolid,
    ThruSections,
    Transform,
    Translate,
)
from .dimension import (
    AngleDimension,
    DiameterDimension,
    LengthDimension,
    RadiusDimension,
)
from .display import DisplayArrow, DisplayLine, DisplayPlane, DisplayText
from .draw import (
    Arc,
    Bezier,
    BSpline,
    BSplineSurface,
    Circle,
    Circuit,
    Edge,
    Ellipse,
    Hyperbola,
    Line,
    MiddlePath,
    Parabola,
    Pdf,
    Plane,
    Polygon,
    Polyline,
    Rectangle,
    Segment,
    Svg,
    Text,
    TrimmedCurve,
    Vertex,
    Wire,
)
from .impl.topology import Topology
from .loaders import load_model
from .mesh import Mesh
from .shape import (
    BBox,
    Box,
    Cone,
    Cylinder,
    Direction,
    Face,
    HalfSpace,
    Material,
    Part,
    Point,
    Prism,
    RawPart,
    RawShape,
    Revol,
    Shape,
    Sphere,
    Texture,
    TopoShape,
    Torus,
    Tube,
    Wedge,
)
from .solver import Solver
from .voxel import Voxel

Loft = ThruSections
Sweep = Pipe
Extrude = Prism
