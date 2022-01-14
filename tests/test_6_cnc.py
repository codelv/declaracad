"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import pytest
from OCCT.TopoDS import TopoDS_Shape
from declaracad.occ.api import load_model


@pytest.mark.parametrize("name", os.listdir('examples/cnc/'))
def test_cnc_examples(qt_app, name):
    path = f"examples/cnc/{name}"
    example = os.path.splitext(name)[0]
    assembly = load_model(path)
    for shape in assembly:
        shape.render()
    output = f'{example}.nc'
    assert os.path.exists(output)
    os.remove(output)  # Cleanup

