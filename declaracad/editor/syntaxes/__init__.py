"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""


def python_syntax():
    from .python_syntax import QPythonCompleter, QPythonHighlighter

    return QPythonCompleter, QPythonHighlighter, "#"


def enaml_syntax():
    from .enaml_syntax import QEnamlCompleter, QEnamlHighlighter

    return QEnamlCompleter, QEnamlHighlighter, "#"


def cpp_syntax():
    from pyqcodeeditor.completers import QCXXCompleter
    from pyqcodeeditor.highlighters import QCXXHighlighter

    return QCXXCompleter, QCXXHighlighter, "//"


def lua_syntax():
    from pyqcodeeditor.completers import QLuaCompleter
    from pyqcodeeditor.highlighters import QLuaHighlighter

    return QLuaCompleter, QLuaHighlighter, "--"


def json_syntax():
    from pyqcodeeditor.highlighters import QJSONHighlighter

    return None, QJSONHighlighter, None


def xml_syntax():
    from .xml_syntax import QXMLHighlighter

    return None, QXMLHighlighter, None


def gcode_syntax():
    from .gcode_syntax import QGCodeCompleter, QGCodeHighlighter

    return QGCodeCompleter, QGCodeHighlighter, "("


# dict[str, tuple[QCompleter, QSyntaxHighlighter, Optional[str]]
SYNTAXES = {
    "": lambda: (None, None, None),
    "python": python_syntax,
    "enaml": enaml_syntax,
    "cpp": cpp_syntax,
    "lua": lua_syntax,
    "json": json_syntax,
    "gcode": gcode_syntax,
    "xml": xml_syntax,
}
