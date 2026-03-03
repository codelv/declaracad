"""
Copyright (c) 2017-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 6, 2015

@author: jrm
"""

import enaml
import enamlx

from declaracad.core.utils import log
from declaracad.core.workbench import DeclaracadWorkbench

with enaml.imports():
    from declaracad.cnc.manifest import CncManifest
    from declaracad.console.manifest import ConsoleManifest
    from declaracad.core.manifest import DeclaracadManifest
    from declaracad.docs.manifest import DocsManifest
    from declaracad.editor.manifest import EditorManifest
    from declaracad.toolbox.manifest import ToolboxManifest
    from declaracad.ui.manifest import UIManifest
    from declaracad.viewer.manifest import ViewerManifest


def main(**kwargs):
    enamlx.install()
    # Start the workbench
    log.info("Workbench starting")
    workbench = DeclaracadWorkbench()

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
