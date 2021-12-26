"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import pytest
from declaracad.cnc import gcode


@pytest.mark.parametrize("name", os.listdir("examples/gcode"))
def test_gcode(name):
    path = "examples/gcode/%s" % name
    data = gcode.parse(path)
    assert len(data.commands) > 0
