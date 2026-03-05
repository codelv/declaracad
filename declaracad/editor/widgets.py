# Copy of enamls scintilla eidtor
import uuid

from atom.api import (
    Atom,
    Constant,
    Enum,
    Event,
    FixedTuple,
    ForwardTyped,
    Int,
    List,
    Typed,
    set_default,
)
from enaml.core.declarative import d_, observe
from enaml.image import Image
from enaml.widgets.control import Control, ProxyControl

#: The available syntaxes for the CodeEditor widget.
from declaracad.editor.syntaxes import SYNTAXES


class CodeEditorDocument(Atom):
    """An opaque class which represents a CodeEditor text document.

    An instance of this class can be shared with multiple CodeEditor
    widgets to enable multiple editor views on the same buffer, or
    to use multiple buffers with the same view.

    """

    #: A uuid which can be used as a handle by the toolkit backend.
    uuid = Constant(factory=lambda: uuid.uuid4().hex)


class CodeEditorIndicator(Atom):
    """An indicator descriptor."""

    #: Starting cursor position of the indicator
    start = FixedTuple(int, int, default=(0, 0))

    #: Stop cursor position of the indicator
    stop = FixedTuple(int, int, default=(0, 0))

    #: Indicator format style
    style = Enum("error", "warning", "info", "hint")


class CodeEditorMarker(Atom):
    """A marker descriptor"""

    #: Line of the marker
    line = Int()

    #: Image to use
    image = Typed(Image)


class ProxyCodeEditor(ProxyControl):
    """The abstract definition of a proxy CodeEditor object."""

    #: A reference to the CodeEditor declaration.
    declaration = ForwardTyped(lambda: CodeEditor)

    def set_document(self, document):
        raise NotImplementedError

    def set_syntax(self, lexer):
        raise NotImplementedError

    def set_theme(self, theme):
        raise NotImplementedError

    def set_settings(self, settings):
        raise NotImplementedError

    def set_zoom(self, zoom):
        raise NotImplementedError

    def get_text(self):
        raise NotImplementedError

    def set_text(self, text):
        raise NotImplementedError

    def set_autocomplete(self, source):
        raise NotImplementedError

    def set_autocompletions(self, options):
        raise NotImplementedError

    def set_indicators(self, indicators):
        raise NotImplementedError

    def set_markers(self, markers):
        raise NotImplementedError


class CodeEditor(Control):
    """A CodeEditor text editing control.

    Notes
    -----
    The 'background', 'foreground', and 'font' attributes have no effect
    on this widget. All styling is supplied via the 'theme' attribute.

    """

    #: Enable autocompletion
    autocomplete = d_(Enum("none", "all", "document", "apis"))

    #: Autocompletion values and call signatures.
    #: Images can be used by appending "?<image_no>" to the completion value.
    #: The images are defined by passing a list of image paths as the
    #: "autocompletion_images" settings key.
    autocompletions = d_(List(str))

    #: Position of the cursor within the editor in the format (line, column)
    #: This is needed for autocompletion engines to determine the current text
    cursor_position = d_(FixedTuple(int, int, default=(0, 0)), writable=False)

    #: The scintilla document buffer to use in the editor. A default
    #: document will be created automatically for each editor. This
    #: value only needs to be supplied when swapping buffers or when
    #: using a single buffer in multiple editors.
    document = d_(Typed(CodeEditorDocument, ()))

    #: The language syntax to apply to the document.
    syntax = d_(Enum(*SYNTAXES.keys()))

    #: The theme to apply to the widget. See the './THEMES' document
    #: for how to create a theme dict for the widget.
    theme = d_(Typed(dict, ()))

    #: The settings to apply to the widget. See the './SETTINGS'
    #: document for how to create a settings dict for the widget.
    settings = d_(Typed(dict, ()))

    #: The zoom factor for the editor. The value is internally clamped
    #: to the range -10 to 20, inclusive.
    zoom = d_(Int())

    #: An event emitted when the text is changed.
    text_changed = d_(Event(), writable=False)

    #: Text Editors expand freely in width by default.
    hug_width = set_default("ignore")

    #: Text Editors expand freely in height by default.
    hug_height = set_default("ignore")

    #: Markers to display.
    markers = d_(List(CodeEditorMarker))

    #: Indicators to display.
    indicators = d_(List(CodeEditorIndicator))

    #: A reference to the ProxyCodeEditor object.
    proxy = Typed(ProxyCodeEditor)

    # --------------------------------------------------------------------------
    # Post Validators
    # --------------------------------------------------------------------------
    def _post_validate_document(self, old, new):
        """Post validate the text document.

        A new document is created when the existing document is set to
        None. This ensures that the proxy object never receives a null
        document and helps keep the state synchronized.

        """
        return new or CodeEditorDocument()

    def _post_validate_theme(self, old, new):
        """ " Post validate the theme.

        The theme is reset to an empty dictionary if set to None.

        """
        return new or {}

    def _post_validate_settings(self, old, new):
        """ " Post validate the settings.

        The settings are reset to an empty dictionary if set to None.

        """
        return new or {}

    # --------------------------------------------------------------------------
    # Observers
    # --------------------------------------------------------------------------
    @observe(
        "document",
        "syntax",
        "theme",
        "settings",
        "zoom",
        "autocomplete",
        "autocompletions",
        "indicators",
        "markers",
    )
    def _update_proxy(self, change):
        """An observer which sends the document change to the proxy."""
        # The superclass implementation is sufficient.
        super()._update_proxy(change)

    # --------------------------------------------------------------------------
    # Public API
    # --------------------------------------------------------------------------
    def get_text(self):
        """Get the text in the current document.

        Returns
        -------
        result : unicode
            The text in the current document.

        """
        if self.proxy_is_active:
            return self.proxy.get_text()
        return ""

    def set_text(self, text):
        """Set the text in the current document.

        Parameters
        ----------
        text : unicode
            The text to apply to the current document.

        """
        if self.proxy_is_active:
            self.proxy.set_text(text)
