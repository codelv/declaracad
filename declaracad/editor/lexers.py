"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on June, 24 2021

@author: jrm
"""
import re
#import ply.yacc as yacc
#parser = yacc.yacc()
from atom.api import Validate
from enaml.scintilla.api import Scintilla
from enaml.scintilla.themes import THEMES
from enaml.qt.QtGui import QColor, QFont
from enaml.qt import scintilla_lexers, scintilla_tokens
from PyQt5.Qsci import QsciLexerCustom


class GCodeLexer(QsciLexerCustom):

    TOKENS = {
        'default': 'Default',
        'comment': "Comment",
        'line_number': "Line",
        'number': "Number",
        'code': "Code",
        'operator': "Operator",
    }

    THEMES = {
        'all': {
            'comment': {
                'color': '#123456',
            },
            'code': {
                'color': '#FF00FF',
            },
        }
    }

    def __init__(self, parent):
        super(GCodeLexer, self).__init__(parent)

    def language(self):
        return "gcode"

    def comment(self, i):
        if i == 1:
            return ['(', ')']

    def code(self, i):
        if i == 4:
            return ['G', 'M', 'N']

    def description(self, style):
        if style == 0:
            return 'default'
        elif style == 1:
            return 'comment'
        elif style == 4:
            return 'code'
        return ''

    def styleText(self, start, end):
        # 1. Initialize the styling procedure
        # ------------------------------------
        self.startStyling(start)

        # 2. Slice out a part from the text
        # ----------------------------------
        text = self.parent().text()[start:end]

        # 3. Tokenize the text
        # ---------------------
        p = re.compile(r"[*]\/|\/[*]|\s+|\w+|\W|\d+")

        # 'token_list' is a list of tuples: (token_name, token_len)Using
        token_list = [(token, len(bytearray(token, "utf-8")))
                      for token in p.findall(text)]
        print(f'Range: {start} to {end}')
        print(f'Tokens: {token_list}')

        # 4. Style the text
        # ------------------
        # 4.1 Check if multiline comment
        multiline_comm_flag = False
        editor = self.parent()
        if start > 0:
            previous_style_nr = editor.SendScintilla(editor.SCI_GETSTYLEAT, start - 1)
            if previous_style_nr == 3:
                multiline_comm_flag = True
        # 4.2 Style the text in a loop
        for i, token in enumerate(token_list):
            tok, index = token
            if multiline_comm_flag:
                self.setStyling(index, 1)
                if tok == ")":
                    multiline_comm_flag = False
            else:
                if tok[0] in ["M", "G", "N"]:
                    # Red style
                    self.setStyling(index, 4)
                elif tok in ["{", "}", "[", "]", "#"]:
                    # Blue style
                    self.setStyling(index, 2)
                elif tok == "(":
                    multiline_comm_flag = True
                    self.setStyling(index, 1)
                else:
                    # Default style
                    self.setStyling(index, 0)


class EnamlLexer(scintilla_lexers.EnamlLexer):
    def keywords(self, kwset):
        from declaracad.occ import api
        kwds = super().keywords(kwset)
        if kwset == 1:
            kwds += ' '.join([a for a in dir(api) if not a.startswith("_")])
        return kwds


CUSTOM_LEXERS = {
    'gcode': GCodeLexer,
}


def install_lexers():
    """ Update enaml's editor

    """
    from pprint import pformat
    items = list(Scintilla.syntax.items)

    scintilla_lexers.LEXERS['enaml'] = EnamlLexer
    scintilla_lexers.LEXERS_INV[EnamlLexer] = 'enaml'

    for name, LexerClass in CUSTOM_LEXERS.items():
        scintilla_lexers.LEXERS[name] = LexerClass
        scintilla_lexers.LEXERS_INV[LexerClass] = name
        scintilla_tokens.TOKENS[name] = LexerClass.TOKENS
        items.append(name)

        # Update themes
        default_theme = LexerClass.THEMES['all']
        for theme_name, theme in THEMES.items():
            if name not in theme:
                custom_theme = LexerClass.THEMES.get(theme_name)
                t = default_theme.copy()
                if custom_theme is not None:
                    t.update(custom_theme)
                theme[name] = t


    # Update syntax items
    Scintilla.syntax.set_validate_mode(Validate.Enum, items)
