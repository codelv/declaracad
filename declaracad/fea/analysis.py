"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""
import warnings
from atom.api import (
    Atom, Value, Typed, ForwardTyped, Enum, Dict, Bool, Float, Property,
    Str, Int
)
from enaml.core.declarative import d_, d_func
from enaml.colors import ColorMember
from declaracad.occ.shape import ProxyShape, Shape


class ProxyAnalysis(ProxyShape):
    #: A reference to the Shape declaration
    declaration = ForwardTyped(lambda: Analysis)

    def set_settings(self, settings):
        raise NotImplementedError


class Analysis(Shape):
    """ A finite element analysis block

    """

    #: Analysis settings
    settings = d_(Dict())

    #: Mesh to perform analysis on
    mesh = d_(Value())

