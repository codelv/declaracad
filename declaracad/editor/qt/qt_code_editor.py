# ------------------------------------------------------------------------------
# Copyright (c) 2026, Jairus Martin.
# Copyright (c) 2013-2025, Nucleic Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ------------------------------------------------------------------------------

import traceback
import warnings
import weakref

from atom.api import Typed, Value
from enaml.colors import parse_color
from enaml.fonts import parse_font
from enaml.qt.q_resource_helpers import (
    QColor_from_Color,
    QFont_from_Font,
)
from enaml.qt.qt_control import QtControl
from enaml.qt.QtCore import Qt
from enaml.qt.QtGui import (
    QColor,
    QFont,
    QWheelEvent,
    QTextCharFormat, QCursor
)
from enaml.qt.QtWidgets import QTextEdit
from pyqcodeeditor.QCodeEditor import QCodeEditor as BaseQCodeEditor
from pyqcodeeditor.QSyntaxStyle import QSyntaxStyle as BaseQSyntaxStyle

from declaracad.editor.syntaxes import SYNTAXES
from declaracad.editor.widgets import ProxyCodeEditor, CodeEditorIndicator


def _make_color(color_str: str) -> QColor:
    """A function which converts a color string into a QColor."""
    color = parse_color(color_str)
    if color is not None:
        return QColor_from_Color(color)
    return QColor()


def _make_font(font_str: str) -> QFont:
    """A function which converts a font string into a QColor."""
    font = parse_font(font_str)
    if font is not None:
        return QFont_from_Font(font)
    return QFont()


class QSyntaxStyle(BaseQSyntaxStyle):
    def __init__(self, theme: dict):
        super().__init__()
        try:
            self._processStyleSchema(theme)
        except Exception as e:
            warnings.warn(f"Can't load style schema: {e}")
            traceback.print_exc()


class QCodeEditor(BaseQCodeEditor):
    zoomLevel: int = 0

    def _updateStyle(self):
        # The original function does not update the background
        if style := self._syntaxStyle:
            self.setStyleSheet(
                "QTextEdit { background-color: %s; selection-background-color: %s; color: %s; }"
                % (
                    style.getFormat("Text").background().color().name(),
                    style.getFormat("Selection").background().color().name(),
                    style.getFormat("Text").foreground().color().name(),
                )
            )

        if self._highlighter:
            self._highlighter.rehighlight()

        self._updateExtraSelection()

    def selectAll(self, enabled: bool = True):
        if enabled:
            super().selectAll()
        else:
            super().textCursor().clearSelection()

    def wheelEvent(self, event: QWheelEvent):
        """Overridden to use ctrl + mouse wheel to zoom"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoomIn()
            else:
                self.zoomOut()
        else:
            super().wheelEvent(event)

    def zoomIn(self, value: int = 1):
        # Overridden to track zoom level
        self.zoomTo(self.zoomLevel + value)

    def zoomOut(self, value: int = 1):
        # Overridden to track zoom level
        self.zoomTo(self.zoomLevel - value)

    def zoomTo(self, value: int):
        """Zoom to a specific zoom level."""
        new_zoom = max(-10, min(20, value))
        if new_zoom > self.zoomLevel:
            super().zoomIn(new_zoom - self.zoomLevel)
        else:
            super().zoomOut(self.zoomLevel - new_zoom)
        self.zoomLevel = new_zoom


class QtCodeEditor(QtControl, ProxyCodeEditor):
    """A Qt implementation of an Enaml ProxyScintilla."""

    #: A weak cache which maps uuid -> QsciDocument.
    doc_cache = weakref.WeakValueDictionary()

    #: A reference to the widget created by the proxy.
    widget = Typed(QCodeEditor)

    #: A reference to the autocomplete API
    autcomplete_api = Value()

    #: A strong reference to the QsciDocument handle.
    doc = Value()

    #: Indicator style to style ID mapping
    _indicator_styles = Typed(dict, ())

    #: Marker image to marker ID mapping
    _marker_images = Typed(dict, ())

    _syntax_style = Typed(QSyntaxStyle)

    # --------------------------------------------------------------------------
    # Initialization API
    # --------------------------------------------------------------------------
    def create_widget(self):
        """Create the underlying label widget."""
        self.widget = QCodeEditor(self.parent_widget())

    def init_widget(self):
        """Initialize the underlying widget."""
        super().init_widget()
        d = self.declaration
        self.set_document(d.document)
        self.set_autocomplete(d.autocomplete)
        self.set_syntax(d.syntax, refresh_style=False)
        self.set_settings(d.settings)
        self.set_zoom(d.zoom)
        self.refresh_style()
        if indicators := d.indicators:
            self.set_indicators(indicators)
        if markers := d.markers:
            self.set_markers(markers)
        self.widget.textChanged.connect(self.on_text_changed)
        self.widget.cursorPositionChanged.connect(self.on_cursor_position_changed)

    def destroy(self):
        """A reimplemented destructor.

        This destructor decrefs its document handle before calling the
        superclass destructor. This prevents a segfault in PyQt.

        """
        # Clear the strong reference to the document. It must be freed
        # *before* the last widget using it is freed or PyQt segfaults.
        del self.doc
        if self.autcomplete_api:
            del self.autcomplete_api
        super().destroy()

    # --------------------------------------------------------------------------
    # Signal Handlers
    # --------------------------------------------------------------------------
    def on_text_changed(self):
        """Handle the 'textChanged' signal on the widget."""
        d = self.declaration
        if d is not None:
            d.text_changed()

    def on_cursor_position_changed(self):
        """Handle the 'cursorPositionChanged' signal on the widget."""
        d = self.declaration
        if d is not None:
            # d.cursor_position = self.widget.getCursorPosition()
            pass

    # --------------------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------------------
    def refresh_style(self):
        """Refresh the theme styling for the widget.

        This method will style the widget and the lexer using the
        current theme that was provided by the declaration object.

        """
        colorcache = {}
        fontcache = {}

        def get_color(color_str):
            if color_str in colorcache:
                return colorcache[color_str]
            color = colorcache[color_str] = _make_color(color_str)
            return color

        def get_font(font_str):
            if font_str in fontcache:
                return fontcache[font_str]
            font = fontcache[font_str] = _make_font(font_str)
            return font

        def pull_color(dct, key, default):
            color = dct.get(key)
            if color is None:
                return default
            return get_color(color)

        def pull_font(dct, key, default):
            font = dct.get(key)
            if font is None:
                return default
            return get_font(font)

        # Setup the various defaults.
        caret_color = QColor(0, 0, 0)
        default_color = QColor(0, 0, 0)
        default_paper = QColor(255, 255, 255)
        default_font = QFont()

        # Update the defaults from the theme's root 'settings' object.
        theme = self.declaration.theme
        settings = theme.get("settings")
        if settings is not None:
            caret_color = pull_color(settings, "caret", caret_color)
            default_color = pull_color(settings, "color", default_color)
            default_paper = pull_color(settings, "paper", default_paper)
            default_font = pull_font(settings, "font", default_font)

        # Apply the default styling for the widget.
        widget = self.widget
        # widget.setCaretForegroundColor(caret_color)
        # widget.setColor(default_color)
        # widget.setPaper(default_paper)
        widget.setFont(default_font)

        style = self._syntax_style = QSyntaxStyle(theme)
        widget.setSyntaxStyle(style)
        # Ensure the lexer and syntax tokens

    def refresh_autocomplete(self):
        """If the lexer changes, update the API options as these depend
        on the lexer.

        """
        d = self.declaration
        if d.autocomplete in ["api", "all"] and d.autocompletions:
            self.set_autocompletions(d.autocompletions)

    def get_indicator_style_id(self, indicator):
        """Get the indicator style id for this indicator. The key
        is simply the style and fg color.

        If the key does not exist, define a new style.

        """
        style = f"{indicator.style},{indicator.color}"
        if style not in self._indicator_styles:
            w = self.widget
            assert w is not None
            # style_id = w.indicatorDefine(INDICATOR_STYLE[indicator.style])
            # w.setIndicatorForegroundColor(_make_color(indicator.color),
            #                              style_id)
            style_id = None
            self._indicator_styles[style] = style_id
        return self._indicator_styles[style]

    # --------------------------------------------------------------------------
    # ProxyCodeEditor API
    # --------------------------------------------------------------------------
    def set_document(self, document):
        """Set the document on the underlying widget."""
        pass

    def set_syntax(self, syntax, refresh_style=True):
        """Set the syntax on the underlying widget."""
        # The old lexer will remain as a child unless deleted.
        Completer = None
        Highlighter = None
        if syntax in SYNTAXES:
            Completer, Highlighter = SYNTAXES[syntax]()
        self.widget.setHighlighter(Highlighter() if Highlighter is not None else None)
        self.widget.setCompleter(Completer() if Completer is not None else None)

    def set_theme(self, theme):
        """Set the styling theme for the widget."""
        self.refresh_style()

    def set_settings(self, settings):
        """Set the settings for the widget."""
        w = self.widget
        if "line_wrap" in settings:
            if settings["line_wrap"]:
                w.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
            else:
                w.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        if "use_tabs" in settings:
            w.setTabReplace(not settings["use_tabs"])
        if "tab_width" in settings:
            w.setTabReplaceSize(settings["tab_width"])
        if "auto_indent" in settings:
            w.setAutoIndentation(settings["auto_indent"])
        if "indent" in settings:
            w.setDefaultIndent(settings["indent"])
        if "auto_parentheses" in settings:
            w.setAutoParentheses(settings["auto_parentheses"])

    def set_zoom(self, zoom):
        """Set the zoom factor on the widget."""
        self.widget.zoomTo(zoom)

    def get_text(self):
        """Get the text in the document."""
        return self.widget.toPlainText()

    def set_text(self, text):
        """Set the text in the document."""
        self.widget.setPlainText(text)

    def set_autocomplete(self, mode):
        """Set the autocompletion mode"""
        pass

    def set_autocompletions(self, options):
        """Set the autocompletion options for when the autocompletion mode
        is in 'all' or 'apis'.

        """
        pass

    def set_autocompletion_images(self, images):
        """Set the images that can be used in autocompletion results."""
        pass

    def set_show_line_numbers(self, show):
        """Set whether line numbers are shown or not by setting
        the margin width of the LineNumber margin.

        """
        pass

    def set_markers(self, markers):
        """Set the markers on the left margin of the widget.

        If the image is not a defined marker, one will be created.

        """
        pass

    def set_indicators(self, indicators: list[CodeEditorIndicator]):
        """Set the indicators of the widget.

        This lets certain text be highlighted or underlined with a given
        style to indicate something (errors) within the editor.

        """
        w = self.widget
        extra_selections = []
        for indicator in indicators:
            # Create cursor
            cursor = w.textCursor()
            cursor.movePosition(QTextCursor.Start);
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.MoveAnchor, indicator.start[0] - 1);
            cursor.movePosition(QTextCursor.StartOfBlock);
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, indicator.start[1]);

            if indicator.stop[0] > indicator.start[0]:
                cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor, indicator.stop[0] - indicator.start[0]);

            cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor);
            cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, indicator.stop[1]);

            # Set style
            style = w._syntaxStyle()
            indicator_format = QTextCharFormat(w.currentCharFormat())
            indicator_format.setFontUnderline(True)
            if indicator.style == "error" or indicator.style == "warning":
                fmt = style.getFormat(indicator.style.title())
                indicator_format.setUnderlineColor(fmt.underlineColor())
                indicator_format.setUnderlineColor(fmt.underlineStyle())
            elif indicator.style == "info":
                fmt = style.getFormat("Warning")
                indicator_format.setUnderlineColor(fmt.underlineColor())
                indicator_format.setUnderlineColor(QTextCharFormat.DotLine)
            elif indicator.style == "hint":
                fmt = style.getFormat("Text")
                indicator_format.setUnderlineColor(fmt.foreground().color())
                indicator_format.setUnderlineColor(QTextCharFormat.DotLine)

            extra_selections.append(QTextEdit.ExtraSelection(cursor, indicator_format))
        w.setExtraSelections(extra_selections)

    # --------------------------------------------------------------------------
    # Reimplementations
    # --------------------------------------------------------------------------
    def set_foreground(self, foreground):
        """Set the foreground color of the widget.

        This reimplementation ignores the foreground setting. The
        foreground color is set by the theme.

        """
        pass

    def set_background(self, background):
        """Set the background color of the widget.

        This reimplementation ignores the background setting. The
        background color is set by the theme.

        """
        pass

    def set_font(self, font):
        """Set the font of the widget.

        This reimplementation ignores the font setting. The font is
        set by the theme.

        """
        pass
