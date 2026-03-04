"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from typing import Optional

from enaml.qt.QtCore import QObject, QRegularExpression
from enaml.qt.QtGui import QTextDocument
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
        self.m_childDefTypePattern: QRegularExpression = QRegularExpression(
            r"(^\s+([A-Za-z]{1}[A-Za-z0-9_]+)\s*\:\s*(([A-Za-z]{1}[A-Za-z0-9_]+)\s*\:\s*)?)"
        )

    def highlightBlock(self, text):
        super().highlightBlock(text)
        matchIterator = self.m_childDefTypePattern.globalMatch(text)
        while matchIterator.hasNext():
            match = matchIterator.next()
            self.setFormat(
                match.capturedStart(2),
                match.capturedLength(2),
                self.syntaxStyle().getFormat("Type"),
            )

            if match.hasCaptured(4):
                self.setFormat(
                    match.capturedStart(4),
                    match.capturedLength(4),
                    self.syntaxStyle().getFormat("Local"),
                )

    def languageFile(self) -> str:
        return resource_path("lang/enaml.json")
