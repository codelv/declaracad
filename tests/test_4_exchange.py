"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from OCCT.TopoDS import TopoDS_Shape

from declaracad.occ.api import load_model


def test_load_dxf(qt_app):
    options = {"from_string": True}
    assembly = load_model(
        """
# Created in DeclaraCAD
from declaracad.occ.api import *
from declaracad.occ.loader import LoadedPart

enamldef Assembly(Part):
    LoadedPart: dxf:
        attr outside_wire = self.topology.wires[5]
        attr inside_wires = [w for w in self.topology.wires if w != outside_wire]
        filename = 'examples/models/25-5050.dxf'
        color = 'red'
    Extrude:
        material = 'aluminium'
        vector = (0, 0, 1000)
        Cut:
            color = 'red'
            Face:
                wires = [dxf.outside_wire]
                color = 'red'
            Looper:
                iterable << dxf.inside_wires
                Face:
                    wires = [loop.item]

    """,
        options,
        ".enaml",
    )[0]
    assert isinstance(assembly.render(), TopoDS_Shape)
