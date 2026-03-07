"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import asyncio
import os
from typing import Optional

from atom.api import Typed

from declaracad.core.protocol import JsonRpcProtocol
from declaracad.core.utils import log
from declaracad.editor.parsers import PARSERS, ParseResult


class LangServerProtocol(JsonRpcProtocol):
    """A very simple langserver to provide background auto-complete,
    linting, and parsing services for the editors.
    """

    #: Event used to know when the server should exit
    finished = Typed(asyncio.Event, ())

    def connection_made(self, transport):
        self.transport = transport
        self.connected = True
        log.debug("Connected to workbench")

    def connection_lost(self, exc):
        self.connected = False
        self.finished.set()

    def on_parse(
        self, filename: str, source: str, version: int
    ) -> Optional[ParseResult]:
        """Parse a file and return any errors"""
        try:
            if not filename:
                return
            log.debug(f"Parsing {filename} version {version}")
            ext = os.path.splitext(filename)[-1].lstrip(".")
            if ext in PARSERS:
                parse = PARSERS[ext]()
                return parse(filename, source)
        except Exception as e:
            log.exception(e)
        return None


async def server(port: int):
    """Connect to the EditorPlugin's server"""
    try:
        log.debug(f"Running langserver {os.getpid()}")
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


def main(port: int, **kwargs):
    """A minimal language server.

    Parameters
    ----------
    port: str
        The port the declaracad application is listening on.
    """
    asyncio.run(server(port))
