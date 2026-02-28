from os.path import dirname, join
from typing import Optional

from enaml.qt.QtCore import QObject
from pyqcodeeditor.QLanguageCompleter import QLanguageCompleter


class QEnamlCompleter(QLanguageCompleter):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

    def languageFile(self) -> str:
        return join(dirname(dirname(dirname(__file__))), "res", "enaml.json")

    def isBuiltinLanguage(self) -> bool:
        return False
