"""
Copyright (c) 2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 23, 2021

@author: jrm
"""
from OCCT.BRepOffsetAPI import BRepOffsetAPI_DraftAngle
from OCCT.gp import gp_Pln

from declaracad.occ.algo import ProxyDraftAngle

from .occ_algo import OccOperation


class OccDraftAngle(OccOperation, ProxyDraftAngle):
    def update_shape(self, change=None):
        d = self.declaration
        child = self.get_first_child()

        # Ignore this operation
        if d.disabled:
            self.shape = child.shape
            return

        draft = BRepOffsetAPI_DraftAngle(child.shape)

        if d.operations:
            for op in d.operations:
                pln_pos, pln_dir = op.neutral_plane
                neutral_plane = gp_Pln(pln_pos.proxy, pln_dir.proxy)
                draft.Add(op.face, op.direction.proxy, op.angle, neutral_plane)
        else:
            a = d.angle
            neutral_plane = gp_Pln(d.position.proxy, d.direction.proxy)
            for f in d.faces:
                draft.Add(f, d.direction.proxy, a, neutral_plane)

        draft.Build()
        if not draft.IsDone():
            raise RuntimeError(f"Could not build draft {d}")
        self.shape = draft.Shape()

    def set_disabled(self, disabled):
        self.update_shape()

    def set_angle(self, angle):
        self.update_shape()

    def set_faces(self, faces):
        self.update_shape()

    def set_operations(self, operations):
        self.update_shape()
