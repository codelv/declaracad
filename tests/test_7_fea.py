"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os

import pytest

# Make sure it installs
from declaracad.fea.impl import fea_factories  # noqa: F401
from declaracad.occ.api import load_model
from declaracad.occ.impl import occ_factories  # noqa: F401

try:
    import pychrono.fea  # noqa: F401
    from SMESH import SMESH  # noqa: F401

    fea_unavailable = False
except ImportError:
    fea_unavailable = True


@pytest.mark.skipif(fea_unavailable, reason="SMESH or pychrono is unavailabe")
@pytest.mark.parametrize("name", os.listdir("examples/fea/"))
def test_fea_examples(qt_app, name):
    path = f"examples/fea/{name}"
    assembly = load_model(path)
    for shape in assembly:
        shape.render()
