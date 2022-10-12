import os
from types import ModuleType

import enaml
from enaml.core.import_hooks import EnamlCompiler
from enaml.core.parser import parse

with enaml.imports():
    from declaracad.occ.loader import LoadedPart  # noqa: F401

from declaracad.occ.api import Shape


def load_declaracad(filename: str, **options) -> list[Shape]:
    """Load a DeclaraCAD model from an enaml file, source, or a shape
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
    from_string: bool = options.get("from_string", False)

    # Parse the enaml file or load from source code
    _, ext = os.path.splitext(filename.lower())
    if from_string:
        source = filename
    else:
        with open(filename, "r") as f:
            source = f.read()
    ast = parse(source)
    code = EnamlCompiler.compile(ast, filename)
    module = ModuleType(filename.rsplit(".", 1)[0])
    module.__file__ = filename
    namespace = module.__dict__
    with enaml.imports():
        exec(code, namespace)
    Assembly = namespace.get("Assembly")
    if Assembly is not None:
        assembly = Assembly()
        if not assembly.name:
            assembly.name = "Source" if from_string else filename
        return [assembly]
    return []
