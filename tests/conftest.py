"""
Copyright (c) 2017-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import pytest

from declaracad.core.app import Application

# Make sure it installs
from declaracad.occ.impl import occ_factories  # noqa: F401


@pytest.fixture(scope="session")
def qt_app():
    """Make sure a QtApplication is active."""
    app = Application.instance()
    if app is None:
        app = Application()
        yield app
        app.stop()
    else:
        yield app
