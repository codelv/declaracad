"""
Copyright (c) 2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from typing import Optional

from enaml.qt.QtCore import QObject, QRegularExpression
from enaml.qt.QtGui import QTextDocument
from pyqcodeeditor.highlighters.QHighlightBlockRule import QHighlightBlockRule
from pyqcodeeditor.highlighters.QHighlightRule import QHighlightRule
from pyqcodeeditor.QLanguage import QLanguage
from pyqcodeeditor.QLanguageCompleter import QLanguageCompleter
from pyqcodeeditor.QStyleSyntaxHighlighter import QStyleSyntaxHighlighter
from pyqcodeeditor.utils import index_of

from declaracad.core.utils import resource_path


class QGCodeCompleter(QLanguageCompleter):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def languageFile(self) -> str:
        return resource_path("lang/gcode.json")

    def isBuiltinLanguage(self) -> bool:
        return False


class QGCodeHighlighter(QStyleSyntaxHighlighter):
    def __init__(self, document: QTextDocument | None = None):
        super().__init__(document)

        self.m_highlightRules: list[QHighlightRule] = []
        self.m_highlightBlockRules: list[QHighlightBlockRule] = []

        self.m_codePattern: QRegularExpression = QRegularExpression(
            r"([A-Z]{1}\-?\d*\.?\d+)"
        )

        # Single line comment
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r";[^\n]*"), "Comment")
        )
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"\([^\n]*"), "Comment")
        )

    def highlightGCode(self, start: int, size: int, code: str, param: str) -> str:
        if code == "X" or code == "Y" or code == "Z":
            style = self.syntaxStyle().getFormat("Type")
        elif code == "G":
            style = self.syntaxStyle().getFormat("Keyword")
        elif code == "M":
            style = self.syntaxStyle().getFormat("Function")
        elif code == "T":
            style = self.syntaxStyle().getFormat("Global")
        elif code == "N":
            style = self.syntaxStyle().getFormat("LineNumber")
        elif code == "I" or code == "J":
            style = self.syntaxStyle().getFormat("Field")
        elif code == "S":
            style = self.syntaxStyle().getFormat("Static")
        elif code == "F":
            style = self.syntaxStyle().getFormat("Preprocessor")
        else:
            style = self.syntaxStyle().getFormat("Error")
        self.setFormat(start, size, style)

    def highlightBlock(self, text):
        matchIterator = self.m_codePattern.globalMatch(text)
        while matchIterator.hasNext():
            match = matchIterator.next()
            start = match.capturedStart()
            size = match.capturedLength()
            code = text[start]
            param = text[start + 1 : start + size]
            self.highlightGCode(start, size, code, param)

        for rule in self.m_highlightRules:
            matchIterator = rule.pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    self.syntaxStyle().getFormat(rule.formatName),
                )

        if not self.m_highlightBlockRules:
            return
        self.setCurrentBlockState(0)
        startIndex = 0
        highlightRuleId = self.previousBlockState()
        if highlightRuleId < 1 or (highlightRuleId > len(self.m_highlightBlockRules)):
            for i, rule in enumerate(self.m_highlightBlockRules):
                # startIndex = text.find(rule.startPattern.pattern())
                startIndex = index_of(text, rule.startPattern, 0)
                if startIndex >= 0:
                    highlightRuleId = i + 1
                    break

        while startIndex >= 0:
            blockRules = self.m_highlightBlockRules[highlightRuleId - 1]
            match = blockRules.endPattern.match(text, startIndex)  # Do not add +1
            endIndex = match.capturedStart()
            if endIndex == -1:
                self.setCurrentBlockState(highlightRuleId)
                matchLength = len(text) - startIndex
            else:
                matchLength = endIndex - startIndex + match.capturedLength()

            self.setFormat(
                startIndex,
                matchLength,
                self.syntaxStyle().getFormat(blockRules.formatName),
            )
            startIndex = index_of(
                text, blockRules.startPattern, startIndex + matchLength
            )

    def languageFile(self) -> str:
        return resource_path("lang/gcode.json")

    def _loadLanguageRules(self):
        language = QLanguage(self.languageFile())
        if not language:
            return
        for key in language.keys():
            names = language.names(key)
            if not names:
                continue
            for name in names:
                self.m_highlightRules.append(
                    QHighlightRule(QRegularExpression(rf"\b{name}\b"), key)
                )
