"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import ast as python_ast

from enaml.core import enaml_ast
from enaml.core.parser import parse as enaml_parse

from declaracad.core.utils import log

from . import Outline, ParseResult, Problem


def parse_enaml(filename: str, source: str) -> ParseResult:
    result = ParseResult()
    try:
        ast = enaml_parse(source, filename)
        outline = []
        # Walk ast and pull out nodes we're insterested in
        for node in ast.body:
            if isinstance(node, enaml_ast.EnamlDef):
                outline.append(
                    Outline(lineno=node.lineno, type="enamldef", label=node.typename)
                )
            elif isinstance(node, enaml_ast.PythonModule):
                for n in node.ast.body:
                    if isinstance(n, python_ast.ClassDef):
                        outline.append(
                            Outline(lineno=n.lineno, type="class", label=n.name)
                        )
                    elif isinstance(n, python_ast.FunctionDef):
                        outline.append(
                            Outline(lineno=n.lineno, type="function", label=n.name)
                        )
        result.outline = outline
    except SyntaxError as e:
        log.debug(e)
        result.problems = [Problem.from_syntaxerror(e)]
        result.outline = [Outline(lineno=e.lineno, label=f"{e}", type="error")]
    return result
