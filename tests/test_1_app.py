"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""

import os
import signal
import subprocess
import sys
import time

import pytest

try:
    from OCCT import OpenGl  # noqa: F401

    opengl_unavailable = False
except ImportError:
    opengl_unavailable = True


@pytest.mark.skipif(opengl_unavailable, reason="OpenGL not available")
def test_app():
    p = subprocess.Popen("declaracad", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for i in range(20):
        time.sleep(1)
        if i == 10:
            if sys.platform == "win32":
                sig = signal.CTRL_C_EVENT
            else:
                sig = signal.SIGINT
            p.send_signal(sig)

        if p.returncode is not None:
            break
    p.wait(10)
    p.kill()
    stdout, stderr = p.communicate()
    for line in stdout.split(b"\n"):
        print(stdout)
    assert b"Workbench stopped" in stdout


@pytest.mark.skipif(opengl_unavailable, reason="OpenGL not available")
def test_render():
    subprocess.check_output(
        "declaracad render examples/fillets.enaml --view_mode top".split()
    )
    assert os.path.exists("fillets.png")
    with open("fillets.png", "rb") as f:
        assert b"PNG" in f.read(10)


def test_themes():
    from declaracad.editor.themes import THEMES

    for name, theme in THEMES.items():
        print(name)
        assert "settings" in theme
        assert "paper" in theme["settings"]
        assert "enaml" in theme
        assert "keyword" in theme["enaml"] or "class_name" in theme["enaml"]
