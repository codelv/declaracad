"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

import ast as python_ast
import asyncio
import os
from ast import parse as python_parse
from typing import Optional

from atom.api import Atom, Enum, Int, List, Str, Typed
from enaml.core import enaml_ast
from enaml.core.parser import parse as enaml_parse

from declaracad.core.protocol import JsonRpcProtocol
from declaracad.core.utils import log


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
            end_offset=e.end_offset,
            end_lineno=e.end_lineno,
            msg=e.msg,
            level="error",
            type=e.__class__.__name__,
        )


class ParseResult(Atom):
    problems = List(Problem)
    outline = List(Outline)


def parse_python(filename: str, source: str) -> ParseResult:
    result = ParseResult()
    try:
        ast = python_parse(source, filename)
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


def parse_gcode(filename: str, source: str) -> ParseResult:
    from declaracad.cnc import gcode

    return [gcode.parse(source)]


PARSERS = {
    "enaml": parse_enaml,
    "python": parse_python,
}


class LangServerProtocol(JsonRpcProtocol):
    """A very simple langserver to provide background auto-complete,
    linting, and parsing services for the editors.
    """

    finished = Typed(asyncio.Event, ())

    def connection_made(self, transport):
        self.transport = transport
        self.connected = True
        log.debug("Connected to workbench")

    def connection_lost(self, exc):
        self.connected = False
        self.finished.set()

    def on_parse(self, filename: str, source: str) -> Optional[ParseResult]:
        """Parse a file and return any errors"""
        log.debug(f"Parsing {filename}")
        try:
            if not filename:
                return
            ext = os.path.splitext(filename)[-1].lstrip(".")
            if ext in PARSERS:
                return PARSERS[ext](filename, source)
        except Exception as e:
            log.exception(e)
        return None


async def main(port: int):
    try:
        log.debug("Running langserver")
        loop = asyncio.get_event_loop()
        transport, protocol = await loop.create_connection(
            lambda: LangServerProtocol(), "127.0.0.1", port
        )
        log.debug("Remote langserver connected!")
        await protocol.finished.wait()
        log.debug("Remote langserver finished!")
    except Exception as e:
        log.error(f"Could not connect to workbench: {e}")
        return
