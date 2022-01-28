"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on July 28, 2018

@author: jrm
"""
import os

import enaml
import enamlx

enamlx.install()

from declaracad import occ

occ.install()
from declaracad.core.app import Application
from declaracad.occ.api import load_model

with enaml.imports():
    from .view import Main


def main(**kwargs):
    app = Application()
    view = Main(model=load_model(kwargs["file"]))
    view.show()
    app.start()


if __name__ == "__main__":
    main()
