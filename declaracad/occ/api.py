"""
Copyright (c) 2017-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 13, 2017

@author: jrm
"""

import enaml
from enaml.core.api import Conditional, Include, Looper  # noqa: F401
from enaml.widgets.api import Timer  # noqa: F401

from .algo import (  # noqa: F401
    Chamfer,
    ChamferData,
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
    RemoveFeatures,
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
from .dimension import (  # noqa: F401
    AngleDimension,
    DiameterDimension,
    LengthDimension,
    RadiusDimension,
)
from .display import DisplayArrow, DisplayLine, DisplayPlane, DisplayText  # noqa: F401
from .draw import (  # noqa: F401
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
from .geom import BBox, Direction, Point  # noqa: F401
from .impl.topology import Topology  # noqa: F401
from .loaders import load_model  # noqa: F401
from .mesh import Mesh  # noqa: F401
from .shape import (  # noqa: F401
    Box,
    Cone,
    Cylinder,
    Export,
    Face,
    HalfSpace,
    Hole,
    Material,
    Part,
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
from .solver import Solver  # noqa: F401
from .voxel import Voxel  # noqa: F401

Loft = ThruSections  # noqa: F401
Sweep = Pipe  # noqa: F401
Extrude = Prism  # noqa: F401

with enaml.imports():
    from declaracad.parts.display import Axis  # noqa: F401
