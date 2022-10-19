"""
Copyright (c) 2018, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 4, 2018

@author: jrm
"""
import json
import sys
import time

import jsonpickle

from declaracad.core.app import Application
from declaracad.occ.api import load_model
from declaracad.occ.exporters import export_shapes


def main(**kwargs):
    """Runs ModelExporter.export() using the passed options.

    Parameters
    ----------
    options: Dict
        A jsonpickle dumped exporter

    """
    model = kwargs.pop("model")
    output = kwargs.pop("output")
    # An Application is required
    Application()
    t0 = time.time()

    sys.stdout.flush()
    # Load the enaml model file
    if model and output:
        options = json.loads(kwargs.pop("options") or "{}")
        if options:
            opts = " ".join([f"{k}={v}" for k, v in options.items()])
            print(f"Exporting {model} to {output} with {opts}...")
        else:
            print(f"Exporting {model} to {output}...")
        parts = load_model(model)

        export_shapes(output, parts, **options)
    else:
        options = kwargs.pop("options")
        exporter = jsonpickle.loads(options)
        assert exporter, f"Failed to load exporter from: {options}"
        print(f"Exporting {exporter.filename} to {exporter.path}...")
        parts = load_model(exporter.filename)
        exporter.export(parts)
    print("Success! Took {} seconds.".format(round(time.time() - t0, 2)))
