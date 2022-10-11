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
def test_example(qt_app, path):
    assembly = load_model(path)
    for shape in assembly:
        assert isinstance(shape.render(), TopoDS_Shape)
