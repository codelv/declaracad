"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""

from declaracad.occ.draw import Svg


def load_svg(filename):
    return [Svg(source=filename)]
