"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from lxml import etree

from . import Outline, ParseResult, Problem


def parse_xml(filename: str, source: str) -> ParseResult:
    result = ParseResult()
    try:
        etree.fromstring(source)
    except SyntaxError as e:
        result.problems = [Problem.from_syntaxerror(e)]
        result.outline = [Outline(lineno=e.lineno, label=f"{e}", type="error")]
    return result
