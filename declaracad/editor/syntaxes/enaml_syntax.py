"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from typing import Optional

from enaml.qt.QtCore import QObject, QRegularExpression
from enaml.qt.QtGui import QTextDocument
from pyqcodeeditor.highlighters.QHighlightRule import QHighlightRule
from pyqcodeeditor.QLanguageCompleter import QLanguageCompleter

from declaracad.core.utils import resource_path

from .python_syntax import QPythonHighlighter


class QEnamlCompleter(QLanguageCompleter):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def languageFile(self) -> str:
        return resource_path("lang/enaml.json")

    def isBuiltinLanguage(self) -> bool:
        return False


class QEnamlHighlighter(QPythonHighlighter):
    def __init__(self, document: Optional[QTextDocument] = None):
        super().__init__(document)
        # self.m_enamldefPattern: QRegularExpression = QRegularExpression(
        #     r"(\b([A-Za-z0-9_]+(?:\.))*([A-Za-z0-9_]+)(?=\())"
        # )
        self.childDefTypePattern: QRegularExpression = QRegularExpression(
            r"(\s+[A-Za-z]{1}[A-Za-z0-9_]+(?:\s*\:\s*([A-Za-z]{1}[A-Za-z0-9_]+\s*\:\s*)?))"
        )

        self.m_highlightRules.append(QHighlightRule(self.childDefTypePattern, "Type"))

    def languageFile(self) -> str:
        return resource_path("lang/enaml.json")
