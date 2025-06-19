"""
Copyright (c) 2025, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import signal

import enaml
import enamlx
from enaml.qt.qt_application import QtApplication

from declaracad.console.plugin import ConsolePlugin

with enaml.imports():
    from declaracad.console.standalone import StandaloneConsole


def main(**kwargs):
    """Launch a standalone ipython console application. Mainly for debugging purposes.
    """
    enamlx.install()
    app = QtApplication()
    plugin = ConsolePlugin()
    window = StandaloneConsole(plugin=plugin)
    window.show()
    signal.signal(signal.SIGINT, lambda *args, **kwargs: app.stop())
    app.start()

