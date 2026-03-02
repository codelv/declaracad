"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import os

import pytest

from declaracad.occ.api import load_model

is_ci = "CI" in os.environ


@pytest.mark.skipif(is_ci, "Disabled in CI")
@pytest.mark.parametrize("name", os.listdir("examples/cnc/"))
def test_cnc_examples(qt_app, name: str):
    path = f"examples/cnc/{name}"
    example = os.path.splitext(name)[0]

    # Generate it
    assembly = load_model(path)
    for shape in assembly:
        assert shape.render()

    # Make sure it exists
    output = f"{example}.nc"
    assert os.path.exists(output)

    with open(output) as f:
        assert "Error generating gcode" not in f.read()

    # Make sure it loads
    toolpath = load_model(output)
    for shape in toolpath:
        assert shape.render()

    # Cleanup
    os.remove(output)
