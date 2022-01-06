"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import pytest
from OCCT.TopoDS import TopoDS_Shape
from declaracad.occ.api import load_model

# Make sure it installs
from declaracad.fea.impl import fea_factories
from declaracad.occ.impl import occ_factories

try:
    import pychrono.fea
    from SMESH import SMESH
    fea_unavailable = False
except ImportError as e:
    fea_unavailable = True


@pytest.mark.skipif(fea_unavailable, reason="SMESH or pychrono is unavailabe")
@pytest.mark.parametrize("name", os.listdir('examples/fea/'))
def test_fea_examples(qt_app, name):
    path = f"examples/fea/{name}"
    example = os.path.splitext(name)[0]
    assembly = load_model(path)
    for shape in assembly:
        shape.render()

