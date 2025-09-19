"""
Copyright (c) 2024, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

from OCCT.BRepAlgoAPI import BRepAlgoAPI_Defeaturing

from declaracad.occ.algo import ProxyRemoveFeatures

from .occ_algo import OccOperation, coerce_shape
from .topology import Topology


class OccRemoveFeatures(OccOperation, ProxyRemoveFeatures):
    reference = (
        "https://dev.opencascade.org/doc/refman/html/"
        "class_b_rep_algo_a_p_i___defeaturing.html"
    )

    def get_input_shape(self):
        d = self.declaration
        if d.shape:
            return coerce_shape(d.shape)
        return self.get_first_child().shape

    def update_shape(self, change=None):
        d = self.declaration
        shape = Topology.cast_shape(self.get_input_shape())
        if d.disabled or not d.features:
            self.shape = shape
            return
        op = BRepAlgoAPI_Defeaturing()
        op.SetShape(shape)
        op.SetRunParallel(d.parallel)
        for face in d.features:
            op.AddFaceToRemove(face)
        op.Build()
        if not op.IsDone():
            raise ValueError("Could not perform feature removal: %s" % d)
        self.shape = op.Shape()

    def set_disabled(self, disabled: bool):
        self.update_shape()

    def set_parallel(self, parallel: bool):
        self.update_shape()

    def set_shape(self, shape):
        self.update_shape()

    def set_features(self, features):
        self.update_shape()
