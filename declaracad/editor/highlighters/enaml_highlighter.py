from os.path import dirname, join
from typing import Optional

from enaml.qt.QtCore import QRegularExpression
from enaml.qt.QtGui import QTextDocument
from pyqcodeeditor.highlighters import QPythonHighlighter
from pyqcodeeditor.highlighters.QHighlightRule import QHighlightRule
from pyqcodeeditor.QLanguage import QLanguage


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
        return join(dirname(dirname(dirname(__file__))), "res", "enaml.json")

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
