"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 1, 2021

@author: jrm
"""
import warnings

try:
    from polyfempy import Settings, Solver
except ImportError as e:
    warnings.warn(e)
    Settings = Solver = None


from declaracad.fea.analysis import ProxyAnalysis, Analysis
from declaracad.occ.impl.occ_shape import OccDependentShape


class FeaAnalysis(OccDependentShape, ProxyAnalysis):
    pass
