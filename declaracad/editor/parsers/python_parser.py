"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import ast as python_ast

from declaracad.core.utils import log

from . import Outline, ParseResult, Problem


def parse_python(filename: str, source: str) -> ParseResult:
    result = ParseResult()
    try:
        ast = python_ast.parse(source, filename)
        outline = []
        # Walk ast and pull out nodes we're insterested in
        for node in ast.body:
            if isinstance(node, python_ast.ClassDef):
                outline.append(
                    Outline(lineno=node.lineno, type="class", label=node.name)
                )
            elif isinstance(node, python_ast.FunctionDef):
                outline.append(
                    Outline(lineno=node.lineno, type="function", label=node.name)
                )
        result.outline = outline
    except SyntaxError as e:
        log.debug(e)
        result.problems = [Problem.from_syntaxerror(e)]
        result.outline = [Outline(lineno=e.lineno, label=f"{e}", type="error")]
    return result
