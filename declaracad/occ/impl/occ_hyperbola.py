"""
Copyright (c) 2016-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
from atom.api import Typed, set_default

from OCCT.Geom import Geom_Hyperbola

from declaracad.occ.draw import ProxyHyperbola
from .occ_edge import OccEdge
from .occ_shape import coerce_axis


class OccHyperbola(OccEdge, ProxyHyperbola):
    #: Update the class reference
    reference = set_default('https://dev.opencascade.org/doc/refman/html/'
                            'classgp___hypr.html')

    curve = Typed(Geom_Hyperbola)

    def create_shape(self):
        d = self.declaration
        major = max(d.major_radius, d.minor_radius)
        minor = min(d.major_radius, d.minor_radius)
        curve = self.curve = Geom_Hyperbola(coerce_axis(d.axis), major, minor)
        self.shape = self.make_edge(curve)

    def set_major_radius(self, r):
        self.create_shape()

    def set_minor_radius(self, r):
        self.create_shape()
