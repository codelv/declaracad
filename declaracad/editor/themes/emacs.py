#-----------------------------------------------------------------------------
# Copyright (c) 2017-2022, Nucleic Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
#-----------------------------------------------------------------------------

EMACS_THEME = {
    "python": {
        "class_name": {
            "color": "#0000FF"
        },
        "comment": {
            "color": "#008800",
            "font-style": "italic"
        },
        "comment_bock": {
            "color": "#008800",
            "font-style": "italic"
        },
        "decorator": {
            "color": "#AA22FF"
        },
        "double_quoted_fstring": {
            "color": "#BB4444"
        },
        "double_quoted_string": {
            "color": "#BB4444"
        },
        "function_method_name": {
            "color": "#00A000"
        },
        "highlighted_identifier": {
            "color": "#AA22FF"
        },
        "identifier": {
            "color": "#B8860B"
        },
        "keyword": {
            "color": "#AA22FF",
            "font-weight": "bold"
        },
        "number": {
            "color": "#666666"
        },
        "operator": {
            "color": "#666666"
        },
        "single_quoted_fstring": {
            "color": "#BB4444"
        },
        "single_quoted_string": {
            "color": "#BB4444"
        },
        "triple_double_quoted_fstring": {
            "color": "#BB4444"
        },
        "triple_double_quoted_string": {
            "color": "#BB4444"
        },
        "triple_single_quoted_fstring": {
            "color": "#BB4444"
        },
        "triple_single_quoted_string": {
            "color": "#BB4444"
        },
        "unclosed_string": {
            "border": "1px solid #FF0000"
        }
    },
    "settings": {
        "caret": "#000000",
        "color": "#000000",
        "name": "emacs",
        "paper": "#ffffff"
    }
}

EMACS_THEME['enaml'] = EMACS_THEME['python']
