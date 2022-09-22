#!/usr/bin/env python
"""
Copyright (c) 2017-2022, Jairus Martin.
Distributed under the terms of the GPL v3 License.
The full license is in the file COPYING.txt, distributed with this software.
Created on Dec 13, 2017
"""
import os
import re
import sys
from setuptools import setup, find_packages
from glob import glob
from pybind11.setup_helpers import Pybind11Extension, build_ext

requirements = [
    'enaml>=0.10.4',
    'jsonpickle',
    'qtconsole',
    'numpydoc',
    'markdown',
    'enamlx',
    'asyncqtpy',  # asyncio + qt
    'nest_asyncio',  # avoid some issues with qtconsole in remote viewer
    'pyserial>=3.5',
    'lxml',
    #'QScintilla',
    'PyQt6',
    'PyQt6-QScintilla',
    #'PyQtWebEngine',
    'service_identity',
    'ezdxf',
    'pdf4py',
]


if sys.platform == 'win32':
    requirements.extend([
        'pywin32',
    ])


def find_include(name: str) -> str:
    prefix = os.path.dirname(os.path.dirname(sys.executable))
    return os.path.join(prefix, 'include', name)


def find_version():
    with open('declaracad/__init__.py') as f:
        for line in f:
            m = re.search(r'version = [\'"](.+)["\']', line)
            if m:
                return m.group(1)
    raise Exception("Could not find version in declaracad/__init__.py")


def find_pyocct():
    project_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_dir, "pyOCCT")

pyocct_dir = find_pyocct()

ext_module = Pybind11Extension("declaracad.extensions",
        sources=glob("src/*.cpp"),
        include_dirs=[
            "src",
            find_include('opencascade'),
            os.path.join(pyocct_dir, "inc"),
            os.path.join(pyocct_dir, "src"),
        ],
        libraries=['TKernel', 'TKOpenGl', 'TKVoxel'],
        # define_macros = [('VERSION_INFO', __version__)],
)

setup(
    name='declaracad',
    version=find_version(),
    description='Parametric 3D modeling with enaml and OpenCascade',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='CodeLV',
    author_email='frmdstryr@gmail.com',
    license='GPL3',
    url='https://github.com/codelv/declaracad',
    entry_points={'console_scripts': [
        'declaracad = declaracad:main',
    ]},
    packages=find_packages(),
    package_data={
        'declaracad': ['*/*.enaml', '*/*.png', '*/*.svg'],
    },
    ext_modules=[
        ext_module
    ],
    cmdclass={"build_ext": build_ext},
    python_requires='>=3.10',
    install_requires=requirements,
)
