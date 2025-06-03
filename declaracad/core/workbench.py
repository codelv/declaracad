"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""

from atom.api import Str
from enaml.qt.QtWidgets import QMessageBox
from enaml.workbench.ui.api import UIWorkbench


class DeclaracadWorkbench(UIWorkbench):
    #: Singleton instance
    _instance = None

    #: For error messages
    app_name = Str("DeclaraCAD")

    def __init__(self, *args, **kwargs):
        if DeclaracadWorkbench.instance() is not None:
            raise RuntimeError("Only one workbench may exist!")
        DeclaracadWorkbench._instance = self
        super(DeclaracadWorkbench, self).__init__(*args, **kwargs)

    @classmethod
    def instance(cls):
        return cls._instance

    @property
    def application(self):
        ui = self.get_plugin("enaml.workbench.ui")
        return ui._application

    @property
    def window(self):
        """Return the main UI window or a dialog if it wasn't made yet
        (during loading)

        """
        ui = self.get_plugin("enaml.workbench.ui")
        return ui.window.proxy.widget

    # -------------------------------------------------------------------------
    # Message API
    # -------------------------------------------------------------------------
    def message_critical(self, title, message, *args, **kwargs):
        """Shortcut to display a critical popup dialog."""
        return QMessageBox.critical(
            self.window,
            "{0} - {1}".format(self.app_name, title),
            message,
            *args,
            **kwargs
        )

    def message_warning(self, title, message, *args, **kwargs):
        """Shortcut to display a warning popup dialog."""
        return QMessageBox.warning(
            self.window,
            "{0} - {1}".format(self.app_name, title),
            message,
            *args,
            **kwargs
        )

    def message_information(self, title, message, *args, **kwargs):
        """Shortcut to display an info popup dialog."""
        return QMessageBox.information(
            self.window,
            "{0} - {1}".format(self.app_name, title),
            message,
            *args,
            **kwargs
        )

    def message_about(self, title, message, *args, **kwargs):
        """Shortcut to display an about popup dialog."""
        return QMessageBox.about(
            self.window,
            "{0} - {1}".format(self.app_name, title),
            message,
            *args,
            **kwargs
        )

    def message_question(self, title, message, *args, **kwargs):
        """Shortcut to display a question popup dialog."""
        return QMessageBox.question(
            self.window,
            "{0} - {1}".format(self.app_name, title),
            message,
            *args,
            **kwargs
        )

    def invoke_command(self, command_id, parameters=None, trigger=None):
        """Shortcut to run a command.

        Parameters
        ----------
        command_id : unicode
            The unique identifier of the command to invoke.
        parameters : dict, optional
            The parameters to pass to the command handler.
        trigger : object, optional
            The object which triggered the command.
        Returns
        -------
        result : object
            The return value of the command handler.
        """
        core = self.get_plugin("enaml.workbench.core")
        return core.invoke_command(command_id, parameters or {}, trigger)
