"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sept 8, 2021

@author: jrm
"""

from enaml.qt.qt_factories import QT_FACTORIES


def fea_analysis_factory():
    from .fea_analysis import FeaAnalysis

    return FeaAnalysis


QT_FACTORIES.update({"Analysis": fea_analysis_factory})
