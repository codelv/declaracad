# -----------------------------------------------------------------------------
# Copyright (c) 2017-2022, Nucleic Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# -----------------------------------------------------------------------------
from .breeze import BREEZE_DARK_THEME
from .default import DEFAULT_THEME
from .dracula import DRACULA_THEME

THEMES: dict[str, dict] = {
    "default": DEFAULT_THEME,
    "dracula": DRACULA_THEME,
    "breeze-dark": BREEZE_DARK_THEME,
}
