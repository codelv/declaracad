"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import re

import enaml
from enaml.qt.qt_application import QtApplication

from declaracad.occ.impl import occ_factories  # noqa: F401
from declaracad.viewer.qt import qt_factories  # noqa: F401

with enaml.imports():
    from declaracad.viewer.offscreen import OccViewer, OffscreenRenderer


def export(app: QtApplication, viewer: OccViewer, output: str, **kwargs):
    """Initialize the viewer, take the screenshot and then stop the app"""
    viewer.proxy.init_viewer()

    # Parameters
    for k, v in kwargs.items():
        if hasattr(viewer, k):
            setattr(viewer, k, v)

    viewer.fit_all()
    viewer.take_screenshot(output)
    app.stop()


def main(
    filename: str,
    output: str = "",
    size: str = "1920x1080",
    raytracing: bool = False,
    **kwargs,
):
    """Launch a single viewer application.

    Parameters
    ----------
    filename: str, optional
        The file path to load
    output: str, optional
        The path to output
    size: str, optional
        The size of the image in the format "widthxheight"

    """
    app = QtApplication()
    if not os.path.exists(filename):
        raise ValueError("File %s does not exist!" % filename)
    if not output:
        base = os.path.splitext(os.path.split(filename)[-1])[0]
        output = f"{base}.png"

    width, height = map(int, re.split("x|-", size))
    renderer = OffscreenRenderer(
        initial_size=(width, height),
        filename=filename,
    )
    # Init window but do not show it
    renderer.initialize()
    renderer.activate_proxy()
    viewer = renderer.viewer
    viewer.minimum_size = (width, height)

    if raytracing:
        viewer.raytracing = True
        viewer.shadows = True
        viewer.reflections = True

    app.deferred_call(export, app, viewer, output, **kwargs)
    app.start()
