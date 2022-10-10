"""
Copyright (c) 2021-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on June, 24 2021

@author: jrm
"""
from atom.api import Validate
from enaml.qt import scintilla_lexers, scintilla_tokens
from enaml.scintilla.api import Scintilla

from declaracad.editor.themes import THEMES

from .gcode import QsciLexerGCode

CUSTOM_LEXERS = {
    "gcode": QsciLexerGCode,
}


class EnamlLexer(scintilla_lexers.EnamlLexer):
    def keywords(self, kwset):
        from declaracad.occ import api

        kwds = super().keywords(kwset)
        # kwset == 1 are things like if, and, else, etc..
        # kwset == 2 are builtins but don't seem to be used for anything
        if kwset == 1:
            kwds += " " + " ".join([a for a in dir(api) if not a.startswith("_")])
        return kwds


def install_lexers():
    """Update enaml's editor"""

    items = list(Scintilla.syntax.items)

    scintilla_lexers.LEXERS["enaml"] = EnamlLexer
    scintilla_lexers.LEXERS_INV[EnamlLexer] = "enaml"

    for name, LexerClass in CUSTOM_LEXERS.items():
        scintilla_lexers.LEXERS[name] = LexerClass
        scintilla_lexers.LEXERS_INV[LexerClass] = name
        scintilla_tokens.TOKENS[name] = LexerClass.TOKENS
        items.append(name)

        # Update themes
        default_theme = LexerClass.THEMES["all"]
        for theme_name, theme in THEMES.items():
            if name not in theme:
                custom_theme = LexerClass.THEMES.get(theme_name)
                t = default_theme.copy()
                if custom_theme is not None:
                    t.update(custom_theme)
                elif "python" in theme:
                    # Copy any theme styles with matching tokens
                    python_theme = theme["python"]
                    for token in LexerClass.TOKENS:
                        py_token = LexerClass.STYLE_MAP.get(token, token)
                        if py_token in python_theme:
                            t[token] = python_theme[py_token].copy()
                theme[name] = t

    # Update syntax items
    Scintilla.syntax.set_validate_mode(Validate.Enum, items)
