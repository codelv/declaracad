# declaracad

[![Build Status](https://travis-ci.org/codelv/declaracad.svg?branch=master)](https://travis-ci.org/codelv/declaracad)
[![Build status](https://ci.appveyor.com/api/projects/status/ke9hminkgevkyquc?svg=true)](https://ci.appveyor.com/project/frmdstryr/declaracad)
[![codecov](https://codecov.io/gh/codelv/declaracad/branch/master/graph/badge.svg)](https://codecov.io/gh/codelv/declaracad)

A declarative parametric 3D modeling program built using [OpenCASCADE](https://github.com/LaughlinResearch/pyOCCT)
and [enaml](https://github.com/nucleic/enaml/).


See the new website at [declaracad.com](https://declaracad.com)

> Warning: This is a very early in development and unstable application!


![DeclaraCAD](https://user-images.githubusercontent.com/380158/43459223-d3ddf346-949a-11e8-8b3c-efe60e88818c.gif)

It's similar to [OpenSCAD](http://www.openscad.org/)
in that everything is intended to be defined programatically. However the
language being used is enaml (a superset of python) instead of javascript.
Python users/developers will find this very easy and intuitive.

It's intended to be used along side of an OCC python binding (either pythonocc or pyOCCT)
using either OCC apis directly or the declarative abstractions. You can easily
combind parts from various sources into assemblies.

Now uses [pyOCCT](https://github.com/LaughlinResearch/pyOCCT) but was originally
based on [pythonocc](https://github.com/tpaviot/pythonocc-core) (and I highly recommend pyOCCT!),


See [the project site](https://declaracad.com/).


## Features

#### Modeling

Currently the following 3D features can be used declaratively:

1. Basic shapes (Box, Sphere, Cylinder, Wedge, Torus) see [shapes](declaracad/occ/shape.py)
2. Boolean operations (Cut, Fuse, Common) see [algo](declaracad/occ/algo.py)
3. Fillet and Chamfer edges see [algo](declaracad/occ/algo.py)
4. 3D Drawing (Lines, Arcs, BSplines, Beziers, Circles, etc...) see [draw](declaracad/occ/draw.py)
5. Pipes [algo](declaracad/occ/algo.py)
6. Extrude (Prism), LinearForm, RevolutionForm [algo](declaracad/occ/algo.py)
7. ThickSolid, ThroughSections [algo](declaracad/occ/algo.py)

See the [examples](examples) and the [occ](declaracad/occ/) package.

You can also embed any shape built using [pythonocc](https://github.com/tpaviot/pythonocc-core) directly via a RawShape. See the [sprocket example](https://github.com/codelv/declaracad/blob/master/examples/sprocket.enaml)


#### Viewer

Declaracad uses pythonocc's Qt Viewer and supports basic rotate, pan, zoom.
Each view is rendered in a separate process.

Clipping planes are now supported.

![declaracad-3d-view-clip-planes](https://user-images.githubusercontent.com/380158/44884230-84e61100-ac88-11e8-8bba-3ebd30941371.gif)

#### Editor

Multiple editor views are supported. Basic error checking hinting is implemented.

## Import / export


Currently there is no import support from other 3d types into editable code,
but models can be loaded for display and exported to STL, STEP, or images.

![DeclaraCAD - loading models](https://user-images.githubusercontent.com/380158/34421112-4fcd664e-ebdb-11e7-8f75-ae7c2354dfa7.gif)

Importing 2D paths from SVG (ex Adobe Illustrator, Inkscape, etc..) is possible

![DeclaraCAD import from svg](https://user-images.githubusercontent.com/380158/34210286-5db22d4a-e563-11e7-9b86-6c2f5db73c96.gif)

Models can be exported to STL or STEP formats for use in other programs (ex Simplify3D, FreeCAD, etc..)

![DeclaraCAD export to stl](https://user-images.githubusercontent.com/380158/34184975-d911c43c-e4f0-11e7-88ca-b52e6557ae83.gif)

## Example

This is generates a turners cube of a given number of levels.

```python

from enaml.core.api import Looper
from declaracad.occ.api import Box, Sphere, Cut, Part

enamldef TurnersCube(Part):
    name = "Turners Cube"

    attr levels: int = 3
    Looper:
        iterable << range(1,1+levels)
        Cut:
            Box:
                position = (-loop_item/2.0,-loop_item/2.0,-loop_item/2.0)
                dx = loop_item
                dy = loop_item
                dz = loop_item
            Sphere:
                radius = loop_item/1.5

```

## Docs

The goal is for the building blocks or components to be self documenting.

It's partially there... suggestions are welcome!

![DeclaraCAD - Docs and Toolbox](https://user-images.githubusercontent.com/380158/34372327-d55d057a-eaa1-11e7-97dc-b95f97511f00.gif)

## Installing

There is currently no installer as it's in pre-alpha state. It runs on windows and linux
(have not yet tested osx). To use it:

```bash

#: Install conda or miniconda
#: See https://conda.io/miniconda.html

#: Create a conda env
conda create -n declaracad

#: Activate it (on windows just do `activate declaracad`)
source activate declaracad

#: Install it OCCT and dependencies
conda install -c trelau -c conda-forge pyocct pysmesh

#: Clone the repo
git clone https://github.com/codelv/declaracad.git

#: Go inside the cloned repo
cd declaracad

#: Install declaracad
pip install -e .

```

See running section.

## Running

To run the full application just run `declaracad`.

```bash
declaracad
```

If you want to use your own editor you can run only a view using

```bash
declaracad view <path/to/model.enaml>
```

Use `declaracad -h` and `declaracad <cmd> -h` to see more cli options.


## License

The application is released under the GPL v3 (due to the use of PyQt5 and QScintilla).

## Special thanks to

This project relies on the groundwork laid out by these projects:

- [pyOCCT](https://github.com/LaughlinResearch/pyOCCT)
- [pySMESH](https://github.com/LaughlinResearch/pySMESH)
- [python-occ](https://github.com/tpaviot/pythonocc)
- [enaml](https://github.com/nucleic/enaml)

Please share your appreciation to them for all the hard work creating these projects!
