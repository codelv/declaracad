"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import asyncio

from declaracad.editor import langserver


def main(port: int, **kwargs):
    """A minimal language server.

    Parameters
    ----------
    port: str
        The port the declaracad application is listening on.
    """
    asyncio.run(langserver.main(port))
