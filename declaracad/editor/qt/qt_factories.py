"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

from enaml.qt.qt_factories import QT_FACTORIES


def code_editor_factory():
    from .qt_code_editor import QtCodeEditor

    return QtCodeEditor


QT_FACTORIES.update(
    {
        "CodeEditor": code_editor_factory,
    }
)
