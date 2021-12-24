import os
import enaml
from types import ModuleType
from enaml.core.parser import parse
from enaml.core.import_hooks import EnamlCompiler

from typing import Optional

with enaml.imports():
    from declaracad.occ.loader import LoadedPart


def load_model(filename: str, from_string: bool = False):
    """ Load a DeclaraCAD model from an enaml file, source, or a shape
    supported by the LoadShape node.

    Parameters
    ----------
    filename: str
        Path to the enaml file to load
    from_string: bool
        Whether to interpret the filename as source code

    Returns
    -------
    result: List[occ.shape.Shape]
        A list of shapes that can be passed to the python-occ viewer.

    """

    # Parse the enaml file or load from source code
    _, ext = os.path.splitext(filename.lower())
    if from_string:
        source = filename
    else:
        with open(filename, 'r') as f:
            source = f.read()
    ast = parse(source)
    code = EnamlCompiler.compile(ast, filename)
    module = ModuleType(filename.rsplit('.', 1)[0])
    module.__file__ = filename
    namespace = module.__dict__
    with enaml.imports():
        exec(code, namespace)
    Assembly = namespace.get('Assembly')
    if Assembly is not None:
        assembly = Assembly()
        if not assembly.name:
            assembly.name = "Source" if from_string else filename
        return [assembly]
    return []
