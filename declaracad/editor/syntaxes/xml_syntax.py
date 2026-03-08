"""
MIT License

Copyright (c) 2026 Jairus Martin
Copyright (c) 2024 zimolab
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
from enaml.qt.QtGui import QTextCharFormat, QTextDocument
from pyqcodeeditor.highlighters.QHighlightRule import QHighlightRule
from pyqcodeeditor.QStyleSyntaxHighlighter import QStyleSyntaxHighlighter
from pyqcodeeditor.utils import index_of


class QXMLHighlighter(QStyleSyntaxHighlighter):
    def __init__(self, document: QTextDocument | None = None):
        super().__init__(document)
        self.m_xmlElementRegex = QRegularExpression(
            r"(<[\s]*[/]?[\s]*([^\n][a-zA-Z-_:]*)(?=[\s/>]))"
        )
        self.m_xmlAttributeRegex = QRegularExpression(r"(\w+(?=\=))")
        self.m_xmlValueRegex = QRegularExpression(r'("[^\n"]+"(?=\??[\s/>]))')
        self.m_xmlCommentBeginRegex = QRegularExpression(r"(<!--)")
        self.m_xmlCommentEndRegex = QRegularExpression(r"(-->)")

        self.m_highlightRules: list[QHighlightRule] = []
        for kw in (r"<\\?", r"/>", r">", r"<", r"</", r"\\>>"):
            self.m_highlightRules.append(
                QHighlightRule(QRegularExpression(kw), "Keyword")
            )

    def highlightBlock(self, text: str):
        style = self.syntaxStyle()
        self.highlightByRegex(style.getFormat("Keyword"), self.m_xmlElementRegex, text)

        for rule in self.m_highlightRules:
            self.highlightByRegex(style.getFormat(rule.formatName), rule.pattern, text)

        self.highlightByRegex(style.getFormat("Text"), self.m_xmlAttributeRegex, text)

        self.setCurrentBlockState(0)
        if self.previousBlockState() != 1:
            start_index = index_of(text, self.m_xmlCommentBeginRegex, 0)
        else:
            start_index = 0

        while start_index >= 0:
            match = self.m_xmlCommentEndRegex.match(text, start_index)
            end_index = match.capturedStart()
            comment_length = 0
            if end_index < 0:
                self.setCurrentBlockState(1)
                comment_length = len(text) - start_index
            else:
                comment_length = end_index - start_index + match.capturedLength()
            self.setFormat(start_index, comment_length, style.getFormat("Comment"))
            start_index = index_of(
                text, self.m_xmlCommentEndRegex, start_index + comment_length
            )

        self.highlightByRegex(style.getFormat("String"), self.m_xmlValueRegex, text)

    def highlightByRegex(
        self, format: QTextCharFormat, regex: QRegularExpression, text: str
    ):
        matchIterator = regex.globalMatch(text)
        while matchIterator.hasNext():
            match = matchIterator.next()
            self.setFormat(
                match.capturedStart(),
                match.capturedLength(),
                format,
            )
