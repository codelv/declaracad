"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import enaml
import enamlx
import signal
from enaml.qt.qt_application import QtApplication
from declaracad.editor.plugin import EditorPlugin, Document, install_lexers

with enaml.imports():
    from declaracad.editor.standalone import StandaloneEditor


def main(filename: str, **kwargs):
    """Launch a standalone editor application. Mainly for testing purposes.

    Parameters
    ----------
    filename: str
        The file path to load
    """
    enamlx.install()
    app = QtApplication()
    plugin = EditorPlugin()
    install_lexers()
    editor = StandaloneEditor(plugin=plugin, doc=Document(name=filename, plugin=plugin))
    editor.show()
    signal.signal(signal.SIGINT, lambda *args, **kwargs: app.stop())
    app.start()
