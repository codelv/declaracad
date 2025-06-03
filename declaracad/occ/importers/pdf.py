"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 19, 2022

@author: jrm
"""

from declaracad.occ.draw import Pdf


def load_pdf(filename):
    return [Pdf(source=filename)]
