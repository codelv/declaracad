# Ripped from enaml's qt_scintilla'
import logging
import sys
import weakref

from atom.api import Typed, Value
from enaml.colors import parse_color
from enaml.fonts import parse_font
from enaml.qt import PYQT6_API, QT_API
from enaml.qt.q_resource_helpers import (
    QColor_from_Color,
    QFont_from_Font,
    get_cached_qimage,
)
from enaml.qt.qt_control import QtControl
from enaml.qt.QtCore import QRect, QSize, Qt
from enaml.qt.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPalette,
    QPen,
    QResizeEvent,
    QWheelEvent,
)
from enaml.qt.QtWidgets import QApplication, QPlainTextEdit, QWidget
from pyqcodeeditor.QCodeEditor import QCodeEditor as BaseQCodeEditor

from declaracad.editor.widgets import ProxyCodeEditor

# from .scintilla_lexers import LEXERS, LEXERS_INV
# from .scintilla_tokens import TOKENS


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


class QLineNumberArea(QWidget):
    def __init__(self, parent: "QCodeEditor"):
        self.editor = parent
        super().__init__(parent)

    def sizeHint(self) -> QSize:
        return QSize(self.editor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.editor.lineNumberPaintEvent(event)


class QCodeEditor(BaseQCodeEditor):
    zoomLevel: int = 0
    # def __init__(self, parent):
    #     super().__init__(parent)
    #     self.lineNumberArea = QLineNumberArea(self)
    #     self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
    #     self.updateRequest.connect(self.updateLineNumberArea)
    #     self.cursorPositionChanged.connect(self.highlightCurrentLine)
    #     palette = QApplication.palette()
    #     self.zoomLevel: int = 0
    #     self.lineNumberAreaPadding: int = 10
    #     self.lineNumberAreaBackground = palette.alternateBase()
    #     self.lineNumberAreaTextBrush = palette.brightText()
    #     self.updateLineNumberAreaWidth(0)
    #     self.highlightCurrentLine()
    #     self.setBackgroundVisible(True)
    #
    # def setPaper(self, color: QColor):
    #     self.palette().setColor(QPalette.Base, color)
    #
    # def setColor(self, color: QColor):
    #     self.palette().setColor(QPalette.Text, color)
    #
    # def lineNumberAreaWidth(self) -> int:
    #     digits = 1
    #     n = max(1, self.blockCount())
    #     while n >= 10:
    #         n /= 10
    #         digits += 1
    #     return self.lineNumberAreaPadding + self.fontMetrics().width('9') * digits
    #
    # def updateLineNumberAreaWidth(self, block_count: int):
    #     self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    #
    # def highlightCurrentLine(self):
    #     pass
    #
    # def updateLineNumberArea(self, rect: QRect, dy: int):
    #     lna = self.lineNumberArea
    #     if dy:
    #         lna.scroll(0, dy)
    #     else:
    #         lna.update(0, rect.y(), lna.width(), rect.height())
    #
    #     if rect.contains(self.viewport().rect()):
    #         self.updateLineNumberAreaWidth(0)
    #
    # def lineNumberPaintEvent(self, event):
    #     region = event.rect()
    #     lna = self.lineNumberArea
    #     painter = QPainter(self.lineNumberArea)
    #     painter.fillRect(region, self.lineNumberAreaBackground)
    #     block = self.firstVisibleBlock()
    #     block_number = block.blockNumber()
    #     top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
    #     bottom = top + self.blockBoundingRect(block).height()
    #
    #     painter.setBrush(self.lineNumberAreaTextBrush)
    #     w = self.lineNumberArea.width()-self.lineNumberAreaPadding/2
    #     h = self.fontMetrics().height()
    #     region_top = region.top()
    #     region_bottom = region.bottom()
    #     while block.isValid() and top <= region_bottom:
    #         if block.isVisible() and bottom >= region_top:
    #             painter.drawText(0, top, w, h, Qt.AlignRight, f"{block_number + 1}")
    #
    #         block = block.next()
    #         top = bottombottom = top + self.blockBoundingRect(block).height()
    #         block_number += 1
    #
    # def resizeEvent(self, event: QResizeEvent):
    #     super().resizeEvent(event)
    #     cr = self.contentsRect()
    #     w = self.lineNumberAreaWidth()
    #     self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), w, cr.height()))

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
        if d.indicators:
            self.set_indicators(d.indicators)
        if d.markers:
            self.set_markers(d.markers)
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

            self.refresh_line_number_width()

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

        # Ensure the lexer and syntax tokens

    def refresh_autocomplete(self):
        """If the lexer changes, update the API options as these depend
        on the lexer.

        """
        d = self.declaration
        if d.autocomplete in ["api", "all"] and d.autocompletions:
            self.set_autocompletions(d.autocompletions)

    def refresh_line_number_width(self):
        """When the number of lines changes update the width accordingly.
        Always shows one more than the width of the number of lines.

        """
        w = self.widget
        # Only update it if show_line_numbers=True
        # if w.marginWidth(NUMBER_MARGIN) > 0:
        #    w.setMarginWidth(NUMBER_MARGIN, "0"+str(max(10, w.lines())))

    def get_indicator_style_id(self, indicator):
        """Get the indicator style id for this indicator. The key
        is simply the style and fg color.

        If the key does not exist, define a new style.

        """
        style = "{},{}".format(indicator.style, indicator.color)
        if style not in self._indicator_styles:
            w = self.widget
            # style_id = w.indicatorDefine(INDICATOR_STYLE[indicator.style])
            # w.setIndicatorForegroundColor(_make_color(indicator.color),
            #                              style_id)
            style_id = None
            self._indicator_styles[style] = style_id
        return self._indicator_styles[style]

    # --------------------------------------------------------------------------
    # ProxyScintilla API
    # --------------------------------------------------------------------------
    def set_document(self, document):
        """Set the document on the underlying widget."""
        pass

    def set_syntax(self, syntax, refresh_style=True):
        """Set the syntax on the underlying widget."""
        # The old lexer will remain as a child unless deleted.
        if syntax == "python":
            from pyqcodeeditor.completers import QPythonCompleter
            from pyqcodeeditor.highlighters import QPythonHighlighter

            self.widget.setHighlighter(QPythonHighlighter())
            self.widget.setCompleter(QPythonCompleter())
        elif syntax == "enaml":
            from ..completers import QEnamlCompleter
            from ..highlighters import QEnamlHighlighter

            self.widget.setHighlighter(QEnamlHighlighter())
            self.widget.setCompleter(QEnamlCompleter())

    def set_theme(self, theme):
        """Set the styling theme for the widget."""
        self.refresh_style()

    def set_settings(self, settings):
        """Set the settings for the widget."""
        pass

    def set_zoom(self, zoom):
        """Set the zoom factor on the widget."""
        # self.widget.zoomTo(zoom)
        pass

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

    def set_indicators(self, indicators):
        """Set the indicators of the widget.

        This lets certain text be highlighted or underlined with a given
        style to indicate something (errors) within the editor.

        """
        pass

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
