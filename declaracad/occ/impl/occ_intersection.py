"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Sep 27, 2016

@author: jrm
"""
from atom.api import set_default
from OCCT.BRepAlgoAPI import BRepAlgoAPI_Section

from declaracad.occ.algo import ProxyIntersection

from .occ_algo import OccBooleanOperation, coerce_shape
from .topology import Topology


class OccIntersection(OccBooleanOperation, ProxyIntersection):
    reference = set_default(
        "https://dev.opencascade.org/doc/overview/html/"
        "occt_user_guides__boolean_operations.html#occt_algorithms_10a"
    )

    op = set_default(BRepAlgoAPI_Section)
