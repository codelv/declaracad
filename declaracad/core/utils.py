"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""

import logging
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from typing import Any, Optional

from enaml.icon import Icon, IconImage
from enaml.image import Image

# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
log = logging.getLogger("declaracad")


def clip(s: Any, n: int = 1000) -> str:
    """Shorten the name of a large value when logging"""
    v = str(s)
    if len(v) > n:
        v[:n] + "..."
    return v


# -----------------------------------------------------------------------------
# Icon and Image helpers
# -----------------------------------------------------------------------------
#: Cache for icons
_IMAGE_CACHE: dict[str, Image] = {}


def resource_path(name: str) -> str:
    """Get the path of a file in the resources folder."""
    path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(path, "res", *name.split("/"))


def icon_path(name: str) -> str:
    """Load an icon from the res/icons folder using the name
    without the .png

    """
    return resource_path(f"icons/{name}.png")


def load_image(name: str) -> Image:
    """Get and cache an enaml Image for the given icon name."""
    path = icon_path(name)
    if path not in _IMAGE_CACHE:
        with open(path, "rb") as f:
            data = f.read()
        _IMAGE_CACHE[path] = Image(data=data)
    return _IMAGE_CACHE[path]


def load_icon(name: str) -> Icon:
    img = load_image(name)
    icg = IconImage(image=img)
    return Icon(images=[icg])


def menu_icon(name: str) -> Optional[Icon]:
    """Icons don't look good on Linux/osx menu's"""
    if sys.platform == "win32":
        return load_icon(name)
    return None


def open_folder(path: str):
    """Open the folder in the system file explorer"""
    if sys.platform == "win32":
        os.startfile(path)
    else:
        cmd = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([cmd, path])


@contextmanager
def log_time(start_message: str, done_message: str = "Done! ({} s)"):
    log.debug(start_message)
    t = time.time()
    yield
    log.debug(done_message.format(round((time.time() - t), 2)))
