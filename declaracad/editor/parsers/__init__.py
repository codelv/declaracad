"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from atom.api import Atom, Enum, Int, List, Str


class Outline(Atom):
    lineno = Int()
    label = Str()
    type = Enum("function", "class", "enamldef", "error")


class Problem(Atom):
    lineno = Int()
    offset = Int()
    end_lineno = Int()
    end_offset = Int()
    msg = Str()
    type = Str()
    level = Enum("error", "warning", "info", "hint")

    @classmethod
    def from_syntaxerror(cls, e: SyntaxError) -> "Problem":
        return cls(
            lineno=e.lineno,
            offset=e.offset,
            end_offset=e.offset if e.end_offset is None else e.end_offset,
            end_lineno=e.lineno if e.end_lineno is None else e.end_lineno,
            msg=e.msg,
            level="error",
            type=e.__class__.__name__,
        )


class ParseResult(Atom):
    problems = List(Problem)
    outline = List(Outline)


def enaml_parser():
    # Import the enaml parser
    from .enaml_parser import parse_enaml

    return parse_enaml


def python_parser():
    # Import the python parser
    from .python_parser import parse_python

    return parse_python


PARSERS = {
    "enaml": enaml_parser,
    "python": python_parser,
}
