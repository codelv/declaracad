"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""

import os

import enaml
import jsonpickle as pickle
from atom.api import Str
from enaml.widgets.api import Container
from enaml.workbench.ui.api import Workspace

from declaracad import get_log_dir
from declaracad.core.utils import log

with enaml.imports():
    from .manifest import UIManifest


class DeclaracadWorkspace(Workspace):
    """A custom Workspace class for the crash course example."""

    #: Storage for the plugin manifest's id.
    _manifest_id = Str()

    #: Where the workspace is stored
    _workspace_file = Str()

    def _default__workspace_file(self):
        return os.path.join(get_log_dir(), "declaracad.workspace.db")

    def start(self):
        """Start the workspace instance.

        This method will create the container content and register the
        provided plugin with the workbench.

        """
        self.content = Container(padding=0)
        manifest = UIManifest()
        self._manifest_id = manifest.id
        try:
            self.workbench.register(manifest)
        except ValueError:
            #: Already registered
            pass
        self.workbench.get_plugin("declaracad.ui")
        self.load_area()

    def stop(self):
        """Stop the workspace instance.

        This method will unregister the workspace's plugin that was
        registered on start.

        """
        self.save_area()
        self.workbench.unregister(self._manifest_id)

    def save_area(self):
        """Save the dock area for the workspace."""
        area = self.content.find("dock_area")
        try:
            with open(self._workspace_file, "w") as f:
                f.write(pickle.dumps(area))
        except Exception as e:
            log.debug("Error saving dock area: {}".format(e))
            return e

    def load_area(self):
        """Load the dock area into the workspace content."""
        area = None
        plugin = self.workbench.get_plugin("declaracad.ui")
        try:
            with open(self._workspace_file, "r") as f:
                area = pickle.loads(f.read())
        except Exception as e:
            log.debug(e)
        if area is None:
            log.debug("Creating new area")
            area = plugin.create_new_area()
        else:
            log.debug("Loading existing doc area")
        area.set_parent(self.content)
