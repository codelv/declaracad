"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import enaml
import enamlx

from declaracad.core.app import Application
from declaracad.editor.plugin import Document, EditorPlugin

with enaml.imports():
    from declaracad.editor.standalone import StandaloneEditor


def main(filename: str, **kwargs):
    """Launch a standalone editor application. Mainly for testing purposes.

    Parameters
    ----------
    filename: str
        The file path to load
    """
    enamlx.install()  # Needed for KeyEvent
    app = Application()
    plugin = EditorPlugin()
    editor = StandaloneEditor(plugin=plugin, doc=Document(name=filename, plugin=plugin))
    editor.show()
    app.start()
