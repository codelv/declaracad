"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import set_default

from OCCT.BOPAlgo import BOPAlgo_Section

from declaracad.occ.algo import ProxyIntersection
from .occ_algo import OccBooleanOperation, coerce_shape
from .topology import Topology


class OccIntersection(OccBooleanOperation, ProxyIntersection):
    reference = set_default(
        "https://dev.opencascade.org/doc/overview/html/"
        "occt_user_guides__boolean_operations.html#occt_algorithms_10a"
    )

    def update_shape(self, change=None):
        section = BOPAlgo_Section()
        d = self.declaration
        if d.shape1:
            section.AddArgument(coerce_shape(d.shape1))
        if d.shape2:
            section.AddArgument(coerce_shape(d.shape2))
        for c in self.children():
            section.AddArgument(c.shape)
        section.Perform()
        if section.HasErrors():
            raise ValueError("Could not intersect shape %s" % d)
        self.shape = Topology.cast_shape(section.Shape())
