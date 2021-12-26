"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import pytest
from declaracad.occ.impl.occ_factories import OCC_FACTORIES


@pytest.mark.parametrize("name", OCC_FACTORIES.keys())
def test_declaracad_factory(name):
    factory = OCC_FACTORIES[name]
    factory()
