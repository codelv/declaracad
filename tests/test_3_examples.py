"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from glob import glob

import pytest
from OCCT.TopoDS import TopoDS_Shape

from declaracad.occ.api import load_model

# Make sure it installs
from declaracad.occ.impl.occ_factories import OCC_FACTORIES  # noqa: F401

EXAMPLES = glob("examples/*.enaml")


@pytest.mark.parametrize("path", EXAMPLES)
def test_example(qt_app, path: str):
    if "paste" in path:
        pytest.skip("paste test disabled")
        return
    if "voxel" in path:
        pytest.skip("Voxel test disabled")
        return
    if "chamfer_profile" in path:
        try:
            from OCCT.ChFi3d import ChFi3d_Linear
        except ImportError:
            pytest.skip("ChFi3d_Linear profile not available")
            return
    with open(path) as f:
        if "from SMESH" in f.read():
            try:
                import SMESH
            except ImportError:
                pytest.skip("SMESH not available")
                return
    assembly = load_model(path)
    for shape in assembly:
        assert isinstance(shape.render(), TopoDS_Shape)
