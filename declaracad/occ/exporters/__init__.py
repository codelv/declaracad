"""
Copyright (c) 2022, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Oct 18, 2022

@author: jrm
"""

import os
from typing import Any

from declaracad.occ.api import Shape


def export_shapes(filename: str, shapes: list[Shape], **options: Any):
    """Export model to the given filename"""
    path, ext = os.path.splitext(filename.lower())
    try:
        ExporterFactory = EXPORTER_REGISTRY[ext]()
    except KeyError:
        raise Exception(f"Unknown export type: {ext}")
    exporter = ExporterFactory(filename=filename)
    for k, v in options.items():
        setattr(exporter, k, v)
    exporter.export(shapes)


def iges_exporter_factory():
    from declaracad.occ.exporters.iges.exporter import IgesExporter

    return IgesExporter


def step_exporter_factory():
    from declaracad.occ.exporters.step.exporter import StepExporter

    return StepExporter


def stl_exporter_factory():
    from declaracad.occ.exporters.stl.exporter import StlExporter

    return StlExporter


def svg_exporter_factory():
    from declaracad.occ.exporters.svg.exporter import SvgExporter

    return SvgExporter


def vrml_exporter_factory():
    from declaracad.occ.exporters.vrml.exporter import VrmlExporter

    return VrmlExporter


EXPORTER_REGISTRY = {
    ".iges": iges_exporter_factory,
    ".step": step_exporter_factory,
    ".stl": stl_exporter_factory,
    ".svg": svg_exporter_factory,
    ".vrml": vrml_exporter_factory,
}
