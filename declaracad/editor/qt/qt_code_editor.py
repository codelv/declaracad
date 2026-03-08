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
from typing import Any, Optional

from atom.api import Typed, Value
from enaml.colors import parse_color
from enaml.fonts import parse_font
from enaml.qt.q_resource_helpers import (
    QColor_from_Color,
    QFont_from_Font,
)
from enaml.qt.qt_control import QtControl
from enaml.qt.QtCore import QRegularExpression, Qt, Signal
from enaml.qt.QtGui import (
    QColor,
    QFont,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QWheelEvent,
)
from enaml.qt.QtWidgets import QTextEdit
from pyqcodeeditor.QCodeEditor import QCodeEditor as BaseQCodeEditor
from pyqcodeeditor.QSyntaxStyle import UNDERLINE_STYLES
from pyqcodeeditor.QSyntaxStyle import QSyntaxStyle as BaseQSyntaxStyle

from declaracad.editor.syntaxes import SYNTAXES
from declaracad.editor.widgets import CodeEditorIndicator, ProxyCodeEditor


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


def _cursor_move_to(
    cursor: QTextCursor, start: tuple[int, int], end: Optional[tuple[int, int]] = None
):
    """Moves the cursor anchor to the given start line number and column. If an end is given
    set the selection to the end line and column. If either column the block length for
    the respective line numbers do not go beyond the block end.
    """
    cursor.movePosition(QTextCursor.Start)
    cursor.movePosition(QTextCursor.NextBlock, QTextCursor.MoveAnchor, start[0] - 1)
    block = cursor.block()
    if 0 <= start[1] < block.length():
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.MoveAnchor, start[1])
    else:
        # Clip
        cursor.movePosition(QTextCursor.EndOfBlock)

    if end is None:
        return

    # Set end position
    if end[0] > start[0]:
        cursor.movePosition(
            QTextCursor.NextBlock, QTextCursor.KeepAnchor, end[0] - start[0]
        )
        block = cursor.document().findBlock(cursor.anchor())

    if 0 <= end[1] < block.length():
        cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor, end[1])
    else:
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)


class QSyntaxStyle(BaseQSyntaxStyle):
    def __init__(self, theme: dict):
        super().__init__()
        try:
            self._processStyleSchema(theme)
        except Exception as e:
            warnings.warn(f"Can't load style schema: {e}")
            traceback.print_exc()

    def _processStyleSchema(self, style_schema: dict[str, Any]):
        """Overridden because the default doesn't set underlineColor"""
        name = style_schema.get("name")
        if not isinstance(name, str) or name.strip() == "":
            return
        styles = style_schema.get("style")
        if not isinstance(styles, list):
            return
        self._loaded = True

        for style in styles:
            if not isinstance(style, dict):
                continue
            style_name = style.get("name")
            if not isinstance(style_name, str) or style_name.strip() == "":
                continue
            style_format = QTextCharFormat()
            if "background" in style:
                style_format.setBackground(QColor(style["background"]))
            if "foreground" in style:
                style_format.setForeground(QColor(style["foreground"]))
            if style.get("bold") == "true":
                style_format.setFontWeight(QFont.Bold)
            if style.get("italic") == "true":
                style_format.setFontItalic(True)
            if "underlineColor" in style:
                style_format.setUnderlineColor(QColor(style["underlineColor"]))
            if "underlineStyle" in style:
                style_format.setUnderlineStyle(
                    UNDERLINE_STYLES.get(
                        style["underlineStyle"],
                        QTextCharFormat.UnderlineStyle.NoUnderline,
                    )
                )
            self._data[style_name] = style_format


class QCodeEditor(BaseQCodeEditor):
    zoom_level: int = 0
    last_search: Optional[tuple[str | QRegularExpression, int, bool, bool]] = None
    searchWrapped = Signal()
    indicatorReleased = Signal()
    indicators: list[QTextEdit.ExtraSelection] = []

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

    def _updateExtraSelection(self):
        """Overridden to add indicators"""
        extra = []
        self._highlightCurrentLine(extra)
        self._highlightParenthesis(extra)
        self.setExtraSelections(extra + self.indicators)

    def setIndicators(self, indicators: list[QTextEdit.ExtraSelection]):
        self.indicators = indicators
        self._updateExtraSelection()

    def setCursorPosition(self, lineno: int, column: int):
        cursor = self.textCursor()
        _cursor_move_to(cursor, (lineno, column))
        self.setTextCursor(cursor)

    def getCursorPosition(self) -> tuple[int, int]:
        cursor = self.textCursor()
        return (cursor.blockNumber() + 1, cursor.positionInBlock())

    def text(self, lineno: int) -> str:
        """Get the text of the line"""
        block = self.document().findBlockByNumber(lineno - 1)
        return block.text()

    def selectedText(self) -> str:
        """Get the selected text"""
        # If the selected text spans a line break it contains a unicode
        # paragraph separator instead of a new line. The replace reverts it back.
        return self.textCursor().selectedText().replace("\u2029", "\n")

    def hasSelectedText(self) -> bool:
        return self.textCursor().hasSelection()

    def replaceSelectedText(self, text: str):
        cursor = self.textCursor()
        try:
            cursor.beginEditBlock()
            cursor.removeSelectedText()
            cursor.insertText(text)
        finally:
            cursor.endEditBlock()

    def getSelection(self) -> tuple[int, int, int, int]:
        """Returns tuple of start_line, start_col, end_line, end_col"""
        doc = self.document()
        cursor = self.textCursor()
        start_offset = cursor.selectionStart()
        start_block = doc.findBlock(start_offset)
        start_line = start_block.blockNumber() + 1
        start_col = start_offset - start_block.position()
        end_offset = cursor.selectionEnd()
        end_block = doc.findBlock(end_offset)
        end_line = end_block.blockNumber() + 1
        end_col = end_offset - start_block.position()
        return (start_line, start_col, end_line, end_col)

    def setSelection(
        self, start_line: int, start_col: int, end_line: int, end_col: int
    ):
        cursor = self.textCursor()
        _cursor_move_to(cursor, (start_line, start_col), (end_line, end_col))
        self.setTextCursor(cursor)

    def insertAt(self, text: str, lineno: int, col: int):
        pos = self.getCursorPosition()
        self.setCursorPosition(lineno, col)
        self.insertPlainText(text)
        self.setCursorPosition(*pos)

    def lines(self) -> int:
        """Return number of lines"""
        return self.document().lineCount()

    def findFirst(
        self,
        text: str,
        regex: bool = True,
        case_sensitive: bool = False,
        words_only: bool = False,
        wrap: bool = True,
        forward: bool = True,
        line: int = -1,
        index: int = -1,
        show: bool = True,
        posix: bool = False,
    ) -> bool:
        if regex:
            query = QRegularExpression(text)
        else:
            query = text
        flags = QTextDocument.FindFlags()
        if case_sensitive:
            flags |= QTextDocument.FindCaseSensitively
        if words_only:
            flags |= QTextDocument.FindWholeWords
        if not forward:
            flags |= QTextDocument.FindBackward
        self.last_search = (query, flags, wrap, show)
        return self.findNext()

    def findNext(self) -> Optional[bool]:
        search = self.last_search
        if not search:
            return None
        query, flags, wrap, show = search
        cursor = self.textCursor()
        doc = self.document()
        new_cursor = doc.find(query, cursor, flags)
        found = not new_cursor.isNull()
        if wrap and not found:
            cursor.movePosition(QTextCursor.Start)
            new_cursor = doc.find(query, cursor, options=flags)
            found = not new_cursor.isNull()
            self.searchWrapped.emit()
        if found and show:
            self.setTextCursor(new_cursor)
        return found

    def selectAll(self, enabled: bool = True):
        if enabled:
            super().selectAll()
        else:
            cursor = self.textCursor()
            cursor.clearSelection()
            self.setTextCursor(cursor)

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
        self.zoomTo(self.zoom_level + value)

    def zoomOut(self, value: int = 1):
        # Overridden to track zoom level
        self.zoomTo(self.zoom_level - value)

    def zoomTo(self, value: int):
        """Zoom to a specific zoom level."""
        new_zoom = max(-10, min(20, value))
        if new_zoom > self.zoom_level:
            super().zoomIn(new_zoom - self.zoom_level)
        else:
            super().zoomOut(self.zoom_level - new_zoom)
        self.zoom_level = new_zoom


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

    #: Token used for comments
    _comment_token = Typed(str)

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
        self.widget.indicatorReleased.connect(self.on_indicator_clicked)

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
            cursor = self.widget.textCursor()
            d.cursor_position = (cursor.position(), cursor.positionInBlock())

    def on_indicator_clicked(self, data):
        """Handle the 'indicatorReleased' signal on the widget."""
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

    def set_syntax(self, syntax: str, refresh_style=True):
        """Set the syntax on the underlying widget."""
        # The old lexer will remain as a child unless deleted.
        if syntax in SYNTAXES:
            Completer, Highlighter, comment_token = SYNTAXES[syntax]()
        else:
            Completer = Highlighter = comment_token = None
        self.widget.setHighlighter(Highlighter() if Highlighter is not None else None)
        self.widget.setCompleter(Completer() if Completer is not None else None)
        self._comment_token = comment_token

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
        if "show_scrollbars" in settings:
            policy = (
                Qt.ScrollBarAsNeeded
                if settings["show_scrollbars"]
                else Qt.ScrollBarAlwaysOff
            )
            w.setHorizontalScrollBarPolicy(policy)
            w.setVerticalScrollBarPolicy(policy)
        if "show_folding" in settings:
            pass
            # style = w.FoldStyle.NoFoldStyle
            # if plugin.code_folding:
            #     name = plugin.code_fold_style.title().replace('-', '')
            #     style = getattr(w.FoldStyle, f'{name}FoldStyle')
            # w.setFolding(style)

    def set_zoom(self, zoom: int):
        """Set the zoom factor on the widget."""
        self.widget.zoomTo(zoom)

    def get_text(self) -> str:
        """Get the text in the document."""
        return self.widget.toPlainText()

    def set_text(self, text: str):
        """Set the text in the document."""
        self.widget.setPlainText(text)

    def goto_position(self, lineno: int, column: int = 0):
        """Goto the start of the given line and ensure the cursor is visible."""
        w = self.widget
        w.setCursorPosition(lineno, column)
        w.ensureCursorVisible

    def delete_line(self):
        """Delete the current line"""
        w = self.widget
        cursor = w.textCursor()
        # Clear line
        cursor.movePosition(QTextCursor.StartOfBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        # Remove line
        cursor.deleteChar()

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
        style = w._syntaxStyle
        for indicator in indicators:
            # Create cursor
            cursor = w.textCursor()
            _cursor_move_to(cursor, indicator.start, indicator.stop)
            if not cursor.hasSelection():
                # Highlight the whole line
                _cursor_move_to(
                    cursor, (indicator.start[0], 0), (indicator.stop[0], -1)
                )

            # Set style
            indicator_format = QTextCharFormat(w.currentCharFormat())
            indicator_format.setFontUnderline(True)
            if indicator.style == "error" or indicator.style == "warning":
                fmt = style.getFormat(indicator.style.title())
                indicator_format.setUnderlineColor(fmt.underlineColor())
                indicator_format.setUnderlineStyle(fmt.underlineStyle())
            elif indicator.style == "info":
                fmt = style.getFormat("Warning")
                indicator_format.setUnderlineColor(fmt.underlineColor())
                indicator_format.setUnderlineStyle(QTextCharFormat.DotLine)
            elif indicator.style == "hint":
                fmt = style.getFormat("Text")
                indicator_format.setUnderlineColor(fmt.foreground().color())
                indicator_format.setUnderlineStyle(QTextCharFormat.DotLine)

            indicator_format.setToolTip(indicator.title)

            item = QTextEdit.ExtraSelection()
            item.cursor = cursor
            item.format = indicator_format
            extra_selections.append(item)
        w.setIndicators(extra_selections)

    def cut(self):
        self.widget.cut()

    def copy(self):
        self.widget.copy()

    def paste(self):
        self.widget.paste()

    def undo(self):
        self.widget.undo()

    def redo(self):
        self.widget.redo()

    def select_all(self):
        self.widget.selectAll(True)

    def deselect_all(self):
        self.widget.selectAll(False)

    def selected_text(self) -> str:
        return self.widget.selectedText()

    def comment_lines(self):
        """Adds a comment to the given lines"""
        token = self._comment_token
        if not token:
            return
        w = self.widget
        if w.hasSelectedText():
            # Change selection to use full lines
            start_line, start_col, end_line, end_col = w.getSelection()
            w.setSelection(start_line, 0, end_line, len(w.text(end_line)) - 1)
            lines = w.selectedText().split("\n")

            # Determine min whitespace of selected lines
            col = min([len(it) - len(it.lstrip()) for it in lines if it.strip()])

            # Insert comment token and ignoring empty lines
            if col == 0:
                lines = [token + it if it.strip() else it for it in lines]
            else:
                lines = [
                    it[0:col] + token + it[col:] if it.strip() else it for it in lines
                ]

            # Replace with commented text
            w.replaceSelectedText("\n".join(lines))

            # Restore selection
            if lines[-1].strip():  # If we modified the last line
                end_col += len(token)
            w.setSelection(start_line, start_col, end_line, end_col)
        else:
            start_line, start_col = w.getCursorPosition()
            text = w.text(start_line)
            col = len(text) - len(text.lstrip())
            if not text.lstrip().startswith(token):
                w.insertAt(token, start_line, col)

            # Restore cursor pos
            if col < start_col:
                start_col += len(token)
            w.setCursorPosition(start_line, start_col)

    def uncomment_lines(self):
        """Remove comments from selected or current lines"""
        token = self._comment_token
        if not token:
            return
        w = self.widget
        if w.hasSelectedText():
            # Change selection to use full lines
            start_line, start_col, end_line, end_col = w.getSelection()
            lines = []
            for line in w.selectedText().split("\n"):
                startswith_comment = line.lstrip().startswith(token)
                if startswith_comment:
                    line = line.replace(token, "", 1)
                lines.append(line)
            print(lines)
            w.replaceSelectedText("\n".join(lines))

            # If the last line was edited decrease end_col
            if startswith_comment:
                end_col -= len(token)

            w.setSelection(start_line, start_col, end_line, end_col)
        else:
            start_line, start_col = w.getCursorPosition()
            text = w.text(start_line)
            if text.lstrip().startswith(token):
                # Select full line
                w.setSelection(start_line, 0, start_line, len(text))

                # Replace
                w.replaceSelectedText(text.replace(token, "", 1).rstrip("\n"))
                w.setCursorPosition(start_line, start_col - 1)

    def toggle_comments(self):
        """Toggle comments"""
        token = self._comment_token
        if not token:
            return
        w = self.widget
        if w.hasSelectedText():
            start_line, start_col, end_line, end_col = w.getSelection()
        else:
            start_line, start_col = w.getCursorPosition()
        text = w.text(start_line)
        if text.lstrip().startswith(token):
            self.uncomment_lines()
        else:
            self.comment_lines()

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
