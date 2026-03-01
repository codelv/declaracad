def python_syntax():
    from .python_syntax import QPythonCompleter, QPythonHighlighter

    return QPythonCompleter, QPythonHighlighter


def enaml_syntax():
    from .enaml_syntax import QEnamlCompleter, QEnamlHighlighter

    return QEnamlCompleter, QEnamlHighlighter


def cpp_syntax():
    from pyqcodeeditor.completers import QCXXCompleter
    from pyqcodeeditor.highlighter import QCXXHighlighter

    return QCXXCompleter, QCXXHighlighter


def lua_syntax():
    from pyqcodeeditor.completers import QLuaCompleter
    from pyqcodeeditor.highlighter import QLuaHighlighter

    return QLuaCompleter, QLuaHighlighter


def json_syntax():
    from pyqcodeeditor.highlighter import QJSONHighlighter

    return None, QJSONHighlighter


def gcode_syntax():
    from .gcode_syntax import QGCodeCompleter, QGCodeHighlighter

    return QGCodeCompleter, QGCodeHighlighter


SYNTAXES = {
    "": lambda: (None, None),
    "python": python_syntax,
    "enaml": enaml_syntax,
    "cpp": cpp_syntax,
    "lua": lua_syntax,
    "json": json_syntax,
    "gcode": gcode_syntax,
}
