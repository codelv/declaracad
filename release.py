"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file COPYING.txt, distributed with this software.

Created on Dec 5, 2017

@author
"""

import importlib
import os
import sys
from glob import glob
from os.path import dirname
from pathlib import Path

import enaml
from cx_Freeze import Executable, hooks, setup
from cx_Freeze.hooks.qthooks import (
    IS_WINDOWS,
    QtHook,
    _get_qt_files,
    _qt_implementation,
)

import declaracad


def patch_cx_freeze():
    # Patch to fix all libs getting placed in the PySide6 folder
    if IS_WINDOWS:
        return

    def qt_qtcore_patched(self, finder, module) -> None:
        """Include plugins for the module."""
        name = _qt_implementation(module)
        for source, target in _get_qt_files(name, "LibrariesPath", "libQt*.so*"):
            finder.lib_files.setdefault(source, target.as_posix())

    QtHook.qt_qtcore = qt_qtcore_patched


def load_declaracad(finder, module):
    import OCCT

    root = dirname(dirname(dirname(OCCT.__path__[0])))
    if sys.platform == "win32":
        root = os.path.join(root, "Library", "lib")

    if sys.platform == "win32":
        patterns = ["*.lib"]
    elif sys.platform == "darwin":
        patterns = ["*.dylib"]
    else:
        patterns = ["*.so*"]

    # Keep all libraries in venv/lib
    for pattern in patterns:
        for source in Path(root).glob(pattern):
            target = f"lib/{source.name}"
            finder.lib_files.setdefault(source, target)
    finder.include_module("declaracad")


# Normal import does not work
hooks.load_declaracad = load_declaracad


def find_enaml_files(*modules):
    """Find .enaml files to include in the zip"""
    files = {}
    for name in modules:
        mod = importlib.import_module(name)
        mod_path = dirname(mod.__file__)
        pkg_root = dirname(mod_path)

        for file_type in ["enaml", "png"]:
            for f in glob("{}/**/*.{}".format(mod_path, file_type), recursive=True):
                pkg = f.replace(pkg_root + os.path.sep, "")
                files[f] = pkg

    return files.items()


def find_data_files(*modules):
    files = {}
    for name in modules:
        mod_path = name
        pkg_root = name

        for f in glob("{}/**/*.png".format(mod_path), recursive=True):
            pkg = f.replace(pkg_root + os.path.sep, "")
            files[f] = pkg
    return files.items()


def find_fonts() -> list[tuple[str, str]]:
    # Include font config on linux
    if IS_WINDOWS or "CONDA_PREFIX" not in os.environ:
        return []
    etc_dir = os.path.join(os.environ["CONDA_PREFIX"], "etc")
    return [(os.path.join(etc_dir, "fonts"), "etc/fonts")]


patch_cx_freeze()
with enaml.imports():
    setup(
        name="declaracad",
        author="CodeLV",
        author_email="frmdstryr@gmail.com",
        license="GPLv3",
        url="https://github.com/codelv/declaracad/",
        description="A declarative parametric 3D modeling application",
        long_description=open("README.md").read(),
        version=declaracad.version,
        options=dict(
            build_exe=dict(
                packages=[
                    "declaracad",
                    "enaml",
                    "enamlx",
                    "parso",
                    "jedi",  # Needed outsize of zip for autocomplete to work
                    "markdown",
                    "html.parser",
                    "pygments",
                    "ipykernel",
                    "zmq.utils.garbage",  # Needed for embedded qt console
                ],
                include_files=find_fonts(),
                zip_include_packages=[
                    "asttokens",
                    "asyncqtpy",
                    "asyncio",
                    "attr",
                    "backcall",
                    "bytecode",
                    "curses",
                    "chardet",
                    "collections",
                    "concurrent",
                    "ctypes",
                    "colorama",
                    "comm",
                    "dateutil",
                    "distutils",
                    "docutils",
                    "email",
                    "executing",
                    "encodings",
                    "ezdxf",
                    "http",
                    "html",
                    "fontTools",
                    "IPython",
                    "ipython_genutils",
                    "ipykernel",
                    "importlib",
                    "importlib_metadata",
                    "json",
                    "jsonpickle",
                    "jupyter_client",
                    "jupyter_core",
                    "jinja2",
                    "logging",
                    "numpydoc",
                    "multiprocessing",
                    "markdown",
                    "pathlib",
                    "pdf4py",
                    "pygments",
                    "pluggy",
                    "prompt_toolkit",
                    "packaging",
                    "pytz",
                    "pydoc_data",
                    "pycparser",
                    "ptyprocess",
                    "pkg_resources",
                    "platformdirs",
                    "pyparsing",
                    "qtpy",
                    "qtconsole",
                    "re",
                    "sqlite3",
                    "sphinx",
                    "serial",
                    "scipy",
                    "stack_data",
                    "sysconfig",
                    "traitlets",
                    "tornado",
                    "toml",
                    "test",
                    "tomlib",
                    "unittest",
                    "urllib",
                    "wcwidth",
                    "zipfile",
                    "xml",
                    "xmlrpc",
                    "_distutils_hack",
                ],
                zip_includes=find_enaml_files("enaml"),
                excludes=[
                    "alabaster",
                    "babel",
                    "wx",
                    "tkinter",
                    "matplotlib",
                    "matplotlib_inline",
                    "lib2to3",
                    "enamlx.qt.qt_occ_viewer",
                    "zmq.eventloop.minitornado",
                    "sphinx",
                    "vtkmodules",
                    "wheel" "debugpy",
                ],
            )
        ),
        executables=[
            Executable(
                "main.py",
                base="gui",
                icon="declaracad/res/icons/logo." + ("ico" if IS_WINDOWS else "png"),
                target_name="declaracad",
                shortcut_name="DeclaraCAD" if IS_WINDOWS else None,
                shortcut_dir="DesktopFolder" if IS_WINDOWS else None,
                # stdout doesn't
                # base='Win32GUI' is_windows else None
            )
        ],
    )
