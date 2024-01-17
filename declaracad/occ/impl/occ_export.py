"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 18, 2022

@author: jrm
"""
import os

from declaracad.occ.exporters import export_shapes
from declaracad.occ.shape import ProxyExport


class OccExport(ProxyExport):
    def activate_bottom_up(self):
        d = self.declaration
        if d.disabled:
            return
        filename = d.filename
        if d.shapes:
            shapes = d.shapes
        else:
            shapes = d.children
        if shapes and filename:
            try:
                path = os.path.abspath(os.path.expanduser(filename))
                export_shapes(path, shapes, **d.options)
                print(f"Exported {path}")
            except Exception as e:
                print(f"Export failed: {e}")
