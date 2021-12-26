"""
Copyright (c) 2017-2021, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

"""
import os
import sys
import time
import signal
import pytest
import subprocess

# @pytest.mark.skipIf(sys.platform == 'win32', "Doesn't work")
@pytest.mark.skip()
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
        p.poll()
        if p.returncode is not None:
            break
    stdout, stderr = p.communicate()
    # for line in stdout.split(b"\n"):
    #    print(stdout)
    assert b"Workbench stopped" in stdout
