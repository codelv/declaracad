"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 31, 2020

@author: jrm
"""
import os
import enaml
from typing import Optional


def load_model(
    filename: str, options: Optional[dict] = None, loader: Optional[str] = None
):
    """Load shapes in the file by looking up the extension from the loader
    registry.

    Parameters
    ----------
    filename: str
        The file to load. If a file format is given this may also
        be the source code.
    options: Optional[dict]
        Options to past to the loader
    loader: Optional[str]
        Filetype to lookup in the loader registry

    Returns
    -------
    shapes: List[Shape]
        List of shapes to include in the part

    """
    options = options or {}
    if loader:
        if not loader.startswith("."):
            loader = f".{loader}"
        hook = LOADER_REGISTRY[loader.lower()]
    else:
        if not filename or not os.path.exists(filename):
            raise ValueError(f"File '{filename}' does not exist!")
        path, ext = os.path.splitext(filename.lower())
        hook = LOADER_REGISTRY.get(ext)
    if hook is None:
        return []
    handler = hook()
    return handler(filename=filename, **options)


def load_brep():
    from declaracad.occ.importers.brep import load_brep

    return load_brep


def load_gcode():
    from declaracad.occ.importers.gcode import load_gcode

    return load_gcode


def load_iges():
    from declaracad.occ.importers.iges import load_iges

    return load_iges


def load_svg():
    from declaracad.occ.importers.svg import load_svg

    return load_svg


def load_step():
    from declaracad.occ.importers.step import load_step

    return load_step


def load_stl():
    from declaracad.occ.importers.stl import load_stl

    return load_stl


def load_dxf():
    from declaracad.occ.importers.dxf import load_dxf

    return load_dxf


def load_dcad():
    from declaracad.occ.importers.dcad import load_model

    return load_model


# Mapping of filename to function that returns a loader.
# A loader is just a function that takes a filename and returns a
# list of DeclaraCAD shapes. This allows deferring of imports until needed
# which improves startup time.
# Case is forced to lower before checking the mapping.
LOADER_REGISTRY = {
    ".brep": load_brep,
    ".dxf": load_dxf,
    ".iges": load_iges,
    ".igs": load_iges,
    ".gcode": load_gcode,
    ".ncc": load_gcode,
    ".nc": load_gcode,
    ".tap": load_gcode,
    ".svg": load_svg,
    ".stp": load_step,
    ".step": load_step,
    ".stl": load_stl,
    ".enaml": load_dcad,
}
