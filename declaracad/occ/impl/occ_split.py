"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import set_default

from OCCT.BOPAlgo import BOPAlgo_Splitter
from OCCT.TopTools import TopTools_ListOfShape

from declaracad.occ.algo import ProxySplit
from .occ_algo import OccBooleanOperation


class OccSplit(OccBooleanOperation, ProxySplit):
    """Fuse all the child shapes together."""

    reference = set_default(
        "https://dev.opencascade.org/doc/overview/html/"
        "occt_user_guides__boolean_operations.html#occt_algorithms_8"
    )

    def update_shape(self, change=None):
        splitter = BOPAlgo_Splitter()
        d = self.declaration
        tools = TopTools_ListOfShape()
        if d.shape1:
            shape = d.shape1
            splitter.AddArgument(shape)
        else:
            shape = None
        if d.shape2:
            tools.Append(d.shape2)
        for c in self.children():
            if shape:
                tools.Append(c.shape)
            else:
                shape = c.shape
                splitter.AddArgument(shape)
        splitter.SetTools(tools)
        splitter.Perform()
        if splitter.HasErrors():
            raise ValueError("Could not split shape %s" % d)
        self.shape = splitter.Shape()
