"""
MIT License

Copyright (c) 2026 Jairus Martin
Copyright (c) 2024 zimolab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

 --------------------------------
| License of the Origin Project: |
 --------------------------------

MIT License

Copyright (c) 2013-2019 Megaxela

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from enaml.qt.QtCore import QRegularExpression
from enaml.qt.QtGui import QTextDocument
from pyqcodeeditor.completers import QPythonCompleter  # noqa: F401
from pyqcodeeditor.highlighters.QHighlightBlockRule import QHighlightBlockRule
from pyqcodeeditor.highlighters.QHighlightRule import QHighlightRule
from pyqcodeeditor.QLanguage import QLanguage
from pyqcodeeditor.QStyleSyntaxHighlighter import QStyleSyntaxHighlighter
from pyqcodeeditor.utils import index_of

from declaracad.core.utils import resource_path


class QPythonHighlighter(QStyleSyntaxHighlighter):
    def __init__(self, document: QTextDocument | None = None):
        super().__init__(document)

        self.m_highlightRules: list[QHighlightRule] = []
        self.m_highlightBlockRules: list[QHighlightBlockRule] = []

        self.m_includePattern: QRegularExpression = QRegularExpression(r"(import \w+)")
        self.m_functionPattern: QRegularExpression = QRegularExpression(
            r"(\b([A-Za-z0-9_]+(?:\.))*([A-Za-z0-9_]+)(?=\())"
        )
        self.m_defTypePattern: QRegularExpression = QRegularExpression(
            r"(\b([A-Za-z0-9_]+)\s+[A-Za-z]{1}[A-Za-z0-9_]+\s*[;=])"
        )

        self.m_attributePattern: QRegularExpression = QRegularExpression(
            r"(\b([A-Za-z]{1}[A-Za-z0-9_]+)\.([A-Za-z]{1}[A-Za-z0-9_]+))"
        )

        self._loadLanguageRules()

        # Following rules has higher priority to display
        # than language specific keys
        # So they must be applied at last.
        # Numbers
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"(\b(0b|0x){0,1}[\d.']+\b)"), "Number")
        )
        # Strings
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"""("[^\n"]*")"""), "String")
        )
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"""('[^\n"]*')"""), "String")
        )
        # Single line comment
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"#[^\n]*"), "Comment")
        )
        self.m_highlightRules.append(
            QHighlightRule(QRegularExpression(r"#[^\n]*"), "Comment")
        )
        # Multiline string
        self.m_highlightBlockRules.append(
            QHighlightBlockRule(
                QRegularExpression("(''')"),
                QRegularExpression("(''')"),
                "String",
            )
        )
        self.m_highlightBlockRules.append(
            QHighlightBlockRule(
                QRegularExpression(r'(""")'),
                QRegularExpression(r'(""")'),
                "String",
            )
        )

    def highlightBlock(self, text):
        matchIterator = self.m_functionPattern.globalMatch(text)
        while matchIterator.hasNext():
            match = matchIterator.next()
            self.setFormat(
                match.capturedStart(),
                match.capturedLength(),
                self.syntaxStyle().getFormat("Type"),
            )
            self.setFormat(
                match.capturedStart(2),
                match.capturedLength(2),
                self.syntaxStyle().getFormat("Function"),
            )

        matchIterator = self.m_attributePattern.globalMatch(text)
        while matchIterator.hasNext():
            match = matchIterator.next()
            obj = match.captured(1)
            if obj == "self":
                self.setFormat(
                    match.capturedStart(3),
                    match.capturedLength(3),
                    self.syntaxStyle().getFormat("Field"),
                )
            else:
                self.setFormat(
                    match.capturedStart(3),
                    match.capturedLength(3),
                    self.syntaxStyle().getFormat("Static"),
                )


        for rule in self.m_highlightRules:
            matchIterator = rule.pattern.globalMatch(text)
            while matchIterator.hasNext():
                match = matchIterator.next()
                self.setFormat(
                    match.capturedStart(),
                    match.capturedLength(),
                    self.syntaxStyle().getFormat(rule.formatName),
                )

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
        return resource_path("lang/python.json")

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
