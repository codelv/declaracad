"""
Copyright (c) 2021-2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on June, 24 2021

@author: jrm
"""

from typing import Optional

import ply.lex as lex
from enaml.qt.Qsci import QsciLexerCustom


class GCodeLexer:
    lexer = None

    # List of token names.   This is always required
    tokens = (
        "NUMBER",
        "PLUS",
        "MINUS",
        "TIMES",
        "DIVIDE",
        "LPAREN",
        "RPAREN",
        "DOT",
        "COMMA",
        "SPACE",
        "TAB",
        "PERCENT",
        "NEWLINE",
        "CODE",
        "COMMENT",
    )

    # Regular expression rules for simple tokens
    t_PLUS = r"\+"
    t_MINUS = r"-"
    t_TIMES = r"\*"
    t_DIVIDE = r"/"
    t_LPAREN = r"\("
    t_RPAREN = r"\)"
    t_COMMA = r","
    t_SPACE = r"\ "
    t_TAB = r"\t"
    t_NEWLINE = r"\r?\n"
    t_DOT = r"\."
    t_PERCENT = r"%"

    # A regular expression rule with some action code
    def t_NUMBER(self, t):
        r"(\d+\.?\d*|\.\d+)"
        t.lexer.value = float(t.value)
        return t

    def t_COMMENT(self, t):
        r"\(.*"
        t.lexer.value = t.value
        return t

    def t_CODE(self, t):
        r"[_A-Za-z]"
        t.lexer.value = t.value
        return t

    # Error handling rule
    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)
        return t

    # Build the lexer
    def build(self, **kwargs):
        self.lexer = lex.lex(module=self, **kwargs)

    def input(self, data):
        return self.lexer.input(data)

    def __iter__(self):
        return self.lexer.__iter__()


class QsciLexerGCode(QsciLexerCustom):
    # Style IDs
    Default = 0
    Comment = 1
    Line = 2
    Number = 3
    Operator = 4
    Param = 5
    GCode = 6
    MCode = 7
    Speed = 8
    Feed = 9
    Pause = 10
    XPos = 11
    YPos = 12
    ZPos = 13
    Keyword = 14
    IOffset = 15
    JOffset = 16

    # Maps to style ID above
    TOKENS = {
        "default": "Default",
        "comment": "Comment",
        "line_number": "Line",
        "number": "Number",
        "gcode": "GCode",
        "mcode": "MCode",
        "param": "Param",
        "speed": "Speed",
        "feed": "Feed",
        "pause": "Pause",
        "xpos": "XPos",
        "ypos": "YPos",
        "zpos": "ZPos",
        "ioffset": "IOffset",
        "joffset": "JOffset",
        "operator": "Operator",
        "keyword": "Keyword",
    }

    # Map gcode token to python token to copy themes
    STYLE_MAP = {
        "number": "number",
        "gcode": "function_method_name",
        "mcode": "keyword",
        "line_number": "keyword",
    }

    CODES = {
        "G": GCode,
        "M": MCode,
        "N": Line,
        "P": Pause,
        "F": Feed,
        "S": Speed,
        "X": XPos,
        "Y": YPos,
        "Z": ZPos,
        "I": IOffset,
        "J": JOffset,
    }

    THEMES = {
        "all": {
            "comment": {
                "color": "#CCCCCC",
            },
            "keyword": {
                "color": "#FF00FF",
            },
            "gcode": {
                "color": "#110a60",
            },
            "mcode": {
                "color": "#0f48ac",
            },
            "line_number": {
                "color": "#74f69c",
            },
            "param": {
                "color": "#bc007d",
            },
            "speed": {
                "color": "#ffa54c",
            },
            "feed": {
                "color": "#7adf1c",
            },
            "pause": {
                "color": "#0488d0",
            },
            "xpos": {
                "color": "#00a0bc",
            },
            "ypos": {
                "color": "#005bbc",
            },
            "zpos": {
                "color": "#4dbc00",
            },
            "ioffset": {
                "color": "#bc9700",
            },
            "joffset": {
                "color": "#bc7000",
            },
        }
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lexer = GCodeLexer()
        self.lexer.build()

    def language(self) -> str:
        return "gcode"

    def comment(self, i: int) -> Optional[list[str]]:
        if i == 1:
            return ["(", ")"]
        return None

    def code(self, i: int) -> Optional[list[str]]:
        if i == 4:
            return ["G", "M", "N"]
        return None

    def description(self, style: int) -> str:
        if style == 0:
            return "default"
        elif style == 1:
            return "comment"
        elif style == 4:
            return "code"
        return ""

    def styleText(self, start: int, end: int):
        self.startStyling(start)

        # Encode and decode to fix unicode issues...
        data = self.parent().text().encode("utf-8")[start:end]
        text = data.decode()

        lexer = self.lexer
        lexer.input(text)
        # print(f"Range: {start} to {end}")
        set_style = self.setStyling
        state: Optional[str] = None
        code: Optional[str] = None
        style: int = self.Default
        CODES = self.CODES
        for token in lexer:
            i = len(token.value.encode("utf-8"))
            t: str = token.type
            # print((token, i))
            if t == "COMMENT":
                set_style(i, self.Comment)
            elif t == "CODE":
                code = token.value
                assert code is not None
                state = t
                style = CODES.get(code, self.Param)
                set_style(i, style)
            elif t in ("SPACE", "TAB", "NEWLINE", "PERCENT", "DOT"):
                state = None
                set_style(i, self.Default)
            elif t == "NUMBER":
                if state == "CODE":
                    set_style(i, style)
                else:
                    set_style(i, self.Number)
            else:
                set_style(i, self.Default)
