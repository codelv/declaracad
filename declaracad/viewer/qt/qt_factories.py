"""
Copyright (c) 2017-2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 13, 2017

@author: jrm
"""
from enaml.qt.qt_factories import QT_FACTORIES


def occ_viewer_factory():
    from .qt_occ_viewer import QtOccViewer
    return QtOccViewer


def occ_viewer_clipped_plane_factory():
    from .qt_occ_clipped_plane import QtOccViewerClippedPlane
    return QtOccViewerClippedPlane


QT_FACTORIES.update({
    'OccViewer': occ_viewer_factory,
    'OccViewerClippedPlane': occ_viewer_clipped_plane_factory,
})
