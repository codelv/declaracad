"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file COPYING.txt, distributed with this software.

Created on Dec 5, 2017

@author
"""
import os
import sys
import enaml
import importlib
import declaracad
from glob import glob
from os.path import dirname, split, exists
from cx_Freeze import setup, Executable

def find_enaml_files(*modules):
    """ Find .enaml files to include in the zip """
    files = {}
    for name in modules:
        mod = importlib.import_module(name)
        mod_path = dirname(mod.__file__)
        pkg_root = dirname(mod_path)

        for file_type in ['enaml', 'png']:
            for f in glob('{}/**/*.{}'.format(mod_path, file_type),
                          recursive=True):
                pkg = f.replace(pkg_root+os.path.sep, '')
                files[f] = pkg

    return files.items()


def find_data_files(*modules):
    files = {}
    for name in modules:
        mod = importlib.import_module(name)
        mod_path = name
        pkg_root = name

        for f in glob('{}/**/*.png'.format(mod_path), recursive=True):
            pkg = f.replace(pkg_root+os.path.sep, '')
            files[f] = pkg
    return files.items()


def find_extra_libs():
    """ Find all the libTK*.so files """
    import OCCT
    root = dirname(dirname(dirname(OCCT.__path__[0])))

    if sys.platform == 'win32':
        root = os.path.join(root, 'Library', 'lib')
        libs = 'TK*.lib'
    elif sys.platform == 'darwin':
        libs = 'libTK*.dylib'
    else:
        libs = 'libTK*.so'

    results = []
    pattern = os.path.join(root, libs)

    for filename in glob(pattern):
        lib = os.path.split(filename)[-1]
        dest = os.path.join('lib', lib)
        results.append((filename, dest))

    assert results, "No occt libraries found!"
    return results


is_windows = sys.platform == 'win32'

with enaml.imports():
    setup(
        name='declaracad',
        author="CodeLV",
        author_email="frmdstryr@gmail.com",
        license='GPLv3',
        url='https://github.com/codelv/declaracad/',
        description="A declarative parametric 3D modeling application",
        long_description=open("README.md").read(),
        version=declaracad.version,
        options=dict(
            build_exe=dict(
                packages=[
                    'declaracad',
                    'enaml',
                    'enamlx',
                    # 'enaml.core.compiler_helpers',
                    # 'enaml.core.template_',
                    # 'enaml.scintilla.api',
                    # 'enaml.workbench.core.api',
                    # 'enaml.workbench.core.core_plugin',
                    # 'enaml.workbench.ui.ui_plugin',
                    # 'enamlx.widgets.api',
                    "parso",  "jedi", # Needed outsize of zip for autocomplete to work
                    'markdown',
                    'html.parser',
                    'pygments',
                    'ipykernel',
                    'zmq.utils.garbage', # Needed for embedded qt console
                ],
                zip_include_packages=[
                    'asyncqt', 'asyncio', 'attr',
                    'backcall', 'bytecode',
                    'curses', 'chardet', 'collections', 'concurrent', 'ctypes',
                    'colorama',
                    'dateutil', 'distutils', 'docutils',
                    'email',
                    'enamlx',
                    'encodings',
                    'ezdxf',
                    'http',
                    'IPython', 'ipython_genutils', 'ipykernel',
                    'importlib', 'importlib_metadata',
                    'json', 'jsonpickle', 'jupyter_client', 'jupyter_core',
                    'jinja2',
                    'logging',
                    'numpydoc',
                    'multiprocessing',
                    'pygments',  'pluggy', 'prompt_toolkit',
                    'pytz', 'pydoc_data', 'pycparser', 'ptyprocess', 'pkg_resources',
                    'qtpy', 'qtconsole',
                    'sqlite3', 'sphinx', 'serial', 'scipy',
                    'traitlets', 'tornado', 'toml', 'test',
                    'unittest', 'urllib',
                    'wcwidth',
                    'xml', 'xmlrpc',
                    '_distutils_hack',
                ],
                zip_includes=find_enaml_files('enaml'),
                include_files=find_extra_libs(),
                excludes=[
                    'alabaster',
                    'babel',
                    'wx',
                    'tkinter',
                    'matplotlib',
                    'lib2to3',
                    'enamlx.qt.qt_occ_viewer',
                    'zmq.eventloop.minitornado',
                    'sphinx',
                    'vtkmodules',
                    'wheel'
                    'debugpy',
                ],
            )
        ),
        executables=[
            Executable(
                'main.py',
                base="gui",
                icon='declaracad/res/icons/logo.' + ('ico' if is_windows else 'png'),
                target_name='declaracad',
                shortcut_name="DeclaraCAD" if is_windows else None,
                shortcut_dir="DesktopFolder" if is_windows else None,
                # stdout doesn't
                # base='Win32GUI' is_windows else None
            )
        ]
    )
