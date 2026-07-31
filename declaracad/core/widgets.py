"""
Copyright (c) 2017-2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from atom.api import Bool, ForwardTyped, Instance, Int, Typed, set_default
from enaml.core.declarative import d_
from enaml.qt.qt_factories import QT_FACTORIES
from enaml.qt.qt_window import QtWindow
from enaml.qt.QtCore import Qt
from enaml.qt.QtGui import QTextCursor, QTextOption, QWindow
from enaml.qt.QtWidgets import QPlainTextEdit, QWidget
from enaml.widgets.api import DockArea, DockItem, RawWidget, Window
from enaml.workbench.api import Plugin


# -----------------------------------------------------------------------------
# Custom widgets
# -----------------------------------------------------------------------------
class PickableDockItem(DockItem):
    """A custom pickable dock item class."""

    #: Plugin this item uses
    plugin = d_(Instance(Plugin))

    def __getstate__(self):
        """Get the pickle state for the dock item.

        This method saves the necessary state for the dock items used
        in this example. Different applications will have different
        state saving requirements.

        The default __setstate__ method provided on the Atom base class
        provides sufficient unpickling behavior.

        """
        return {"name": self.name, "title": self.title}


class PickableDockArea(DockArea):
    """A custom pickable dock area class."""

    def get_save_items(self):
        """Get the list of dock items to save with this dock area."""
        return [c for c in self.children if isinstance(c, PickableDockItem)]

    def __getstate__(self):
        """Get the pickle state for the dock area.

        This method saves the necessary state for the dock area used
        in this example. Different applications will have different
        state saving requirements.

        """
        state = {
            "name": self.name,
            "layout": self.save_layout(),
            "items": self.get_save_items(),
        }
        return state

    def __setstate__(self, state):
        """Restore the state of the dock area."""
        self.name = state["name"]
        self.layout = state["layout"]
        self.insert_children(None, state["items"])


class EmbeddedWindow(RawWidget):
    """Create a widget that embeds the window from another application.
    This allows you to run expensive operations (ex 3D rendering) without
    blocking the main UI.

    """

    #: Expand by default
    hug_width = set_default("ignore")
    hug_height = set_default("ignore")

    #: Window ID of embedded application
    window_id = d_(Int())

    def create_widget(self, parent):
        window = QWindow.fromWinId(self.window_id)
        return QWidget.createWindowContainer(window, parent)


class PlainTextEdit(RawWidget):
    """QTextEdit used by the MultiLineField is horribly slow at appending
    text. This widget is significantly faster.

    """

    #: Lines to display
    maximum_block_count = d_(Int(500))

    def create_widget(self, parent):
        widget = QPlainTextEdit(parent)
        widget.setReadOnly(True)
        widget.setMaximumBlockCount(self.maximum_block_count)
        widget.setWordWrapMode(QTextOption.NoWrap)
        return widget

    def clear(self):
        """Clear the widget text"""
        if widget := self.get_widget():
            widget.clear()

    def append(self, text: str):
        """Append text to the end of the input"""
        if widget := self.get_widget():
            widget.moveCursor(QTextCursor.End)
            widget.insertPlainText(text)
            widget.moveCursor(QTextCursor.End)

    def scroll_to_end(self):
        if widget := self.get_widget():
            scroll_bar = widget.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())


class QtFramelessWindow(QtWindow):
    declaration = ForwardTyped(lambda: FramelessWindow)

    def creation_flags(self):
        flags = super().creation_flags()
        if self.declaration.frameless:
            flags |= Qt.FramelessWindowHint
        return flags


class FramelessWindow(Window):
    proxy = Typed(QtFramelessWindow)

    #: Frameless
    frameless = d_(Bool())


QT_FACTORIES.update(
    {
        "FramelessWindow": lambda: QtFramelessWindow,
    }
)
