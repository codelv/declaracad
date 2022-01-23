"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import pytest
from OCCT.TopoDS import TopoDS_Shape
from declaracad.occ.api import load_model
from declaracad.occ.impl.occ_factories import OCC_FACTORIES  # Make sure it installs

EXAMPLES = (
    "arcs",
    "bearing",
    "birdhouse",
    "bilo",
    "bolt",
    "bottle",
    "chamfers",
    "dahlgren300z",
    "dimensions",
    "draw",
    "draft_angle",
    "exhaust_flange",
    "faces",
    "fillets",
    "gcode",
    "half_space",
    #'house',
    "intersection",
    "load",
    "middlepath",
    "nemastepper",
    "normal_projection",
    "offsets",
    "operations",
    "pipes",
    "raw_shape",
    #'rib',
    "shapes",
    "split",
    "spring",
    "svg",
    "sweeps",
    "threads",
    "thru_sections",
    "turners_cube",
    "trimmed",
    "vacuum_nozzle",
    "unify",
)


@pytest.mark.parametrize("name", EXAMPLES)
def test_example(qt_app, name):
    path = "examples/%s.enaml" % name
    assembly = load_model(path)
    for shape in assembly:
        assert isinstance(shape.render(), TopoDS_Shape)
