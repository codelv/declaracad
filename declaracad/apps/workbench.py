"""
Copyright (c) 2017-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 6, 2015

@author: jrm
"""
import sys
import signal
import enaml
import faulthandler

faulthandler.enable()

import enamlx

enamlx.install()

from declaracad.core.workbench import DeclaracadWorkbench
from declaracad.core.utils import log

with enaml.imports():
    #: TODO autodiscover these
    from declaracad.core.manifest import DeclaracadManifest
    from declaracad.ui.manifest import UIManifest
    from declaracad.viewer.manifest import ViewerManifest
    from declaracad.console.manifest import ConsoleManifest
    from declaracad.docs.manifest import DocsManifest
    from declaracad.editor.manifest import EditorManifest
    from declaracad.toolbox.manifest import ToolboxManifest
    from declaracad.cnc.manifest import CncManifest

try:
    # Required on Qt 5.10+
    from enaml.qt import QtWebEngineWidgets
except Exception as e:
    log.warning(e)


def main(**kwargs):

    # Start the workbench
    log.info("Workbench starting")
    workbench = DeclaracadWorkbench()

    # Make sure ^C keeps working and does a proper shutdown
    def quit(*args):
        workbench.invoke_command("enaml.workbench.ui.close_window")

    signal.signal(signal.SIGINT, quit)

    # Register plugins
    workbench.register(DeclaracadManifest())
    workbench.register(UIManifest())
    workbench.register(ConsoleManifest())
    workbench.register(DocsManifest())
    workbench.register(ViewerManifest())
    workbench.register(EditorManifest())
    workbench.register(ToolboxManifest())
    workbench.register(CncManifest())

    # Run
    workbench.run()
    log.info("Workbench stopped")


if __name__ == "__main__":
    main()
