"""
Copyright (c) 2025, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import enaml

from declaracad.console.plugin import ConsolePlugin
from declaracad.core.app import Application

with enaml.imports():
    from declaracad.console.standalone import StandaloneConsole


def main(**kwargs):
    """Launch a standalone ipython console application. Mainly for debugging purposes."""
    app = Application()
    plugin = ConsolePlugin()
    window = StandaloneConsole(plugin=plugin)
    window.show()
    app.start()
