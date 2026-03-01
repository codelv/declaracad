"""
Copyright (c) 2018-2019, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on July 28, 2018

@author: jrm
"""

import asyncio
import os
import sys
import traceback

import enaml
from atom.api import Instance, Str, Typed

from declaracad.console.plugin import ConsolePlugin
from declaracad.core.app import AsyncApplication as Application
from declaracad.core.utils import log
from declaracad.viewer.protocol import JsonRpcProtocol, RemoteLogger

with enaml.imports():
    from declaracad.viewer.standalone import ViewerWindow


class ViewerProtocol(JsonRpcProtocol):
    """Use stdio as a json-rpc interface to communicate with external
    processes.

    If --frameless is used, the interface must receive a ping at least every
    60 sec or it will assume it's owner has left and will exit.

    """

    app = Instance(Application)
    view = Typed(ViewerWindow)
    ref = Str()
    logger = Typed(RemoteLogger)

    def connection_made(self, transport):
        self.transport = transport
        self.connected = True
        log.debug("Connected to workbench")
        window_id = int(self.view.proxy.widget.winId())
        self.invoke_method("welcome", self.ref, window_id)

        # Send stdout/stderr to remote connection
        logger = self.logger = RemoteLogger(
            protocol=self, stdout=sys.stdout, stderr=sys.stderr
        )
        logger.attach()

        # Reattach logger
        # for handler in log.handlers:
        #    if getattr(handler, 'stream', None) == logger.stdout:
        #        handler.setStream(logger)

    def connection_lost(self, exc):
        self.logger.detach()
        self.app.stop()

    def on_call(self, method, *args, **kwargs):
        for target in (self.view, self.view.viewer):
            handler = getattr(target, method, None)
            if handler is not None:
                return handler(*args, **kwargs)
        raise AttributeError(method)

    def on_set(self, attr, value):
        for target in (self.view, self.view.viewer):
            if hasattr(target, attr):
                return setattr(target, attr, value)
        raise AttributeError(attr)


async def run_remote(
    app: Application, view: ViewerWindow, filename: str, port: int, ref: str
):
    """Open a connection to the workbench application.

    Parameters
    ----------
    app: Application
        The application instance
    view: ViewerWindow
        The viewer window
    filename: str
        The filename being opened. '-' means read from stdin.
    port: int
        The port of the workbench server.
    ref: str
        The internal name of the viewer item in the workbench.

    """
    try:
        log.debug("Running remote viewer")
        assert app.loop is not None
        transport, protocol = await app.loop.create_connection(
            lambda: ViewerProtocol(app=app, view=view, ref=ref), "127.0.0.1", port
        )
        log.debug("Remote viewer connected!")
    except Exception as e:
        log.error(f"Could not connect to workbench: {e}")
        app.stop()
        return
    view.protocol = protocol
    view.filename = filename


async def run_local(app: Application, view: ViewerWindow, filename: str, watch: bool):
    """Set the filename for the viewer to load and watch for changes"""
    log.debug("Running local viewer")
    view.filename = filename
    if not watch:
        return

    last_mtime = os.stat(filename).st_mtime
    while app.running:
        await asyncio.sleep(1)
        mtime = os.stat(filename).st_mtime
        if mtime != last_mtime:
            log.info(f"{filename} changed, reloading")
            try:
                view.version += 1
            except Exception:
                traceback.print_exc()
            last_mtime = mtime
    log.warning("File watcher stopped")


def main(
    filename: str = "-", port: int = 0, watch: bool = False, ref: str = "", **kwargs
):
    """Launch a single viewer application.

    Parameters
    ----------
    filename: str, optional
        The file path to load
    port: int, optional
        The workbench application server port. If given the viewer will
        open in frameless mode and attempt to connect to the port.
    watch: bool
        If True automatically reload when the file changes. This is only
        applicable if the port argument is not given.
    ref: str, optional
        Viewer reference ID from the application. Can be any str if testing.
    """
    log.debug(f"Starting viewer pid={os.getpid()} cwd={os.getcwd()} port={port}")

    # Set default surface format to avoid OCCT warnings
    from enaml.qt.QtGui import QSurfaceFormat

    surface_format = QSurfaceFormat()
    surface_format.setDepthBufferSize(24)
    surface_format.setStencilBufferSize(8)
    surface_format.setVersion(3, 2)
    surface_format.setProfile(QSurfaceFormat.CoreProfile)
    QSurfaceFormat.setDefaultFormat(surface_format)

    app = Application(platform="xcb")

    if not port and not os.path.exists(filename):
        raise ValueError(f"File {filename} does not exist!")
    if port and not ref:
        raise ValueError("A ref is required when port is given")

    # Required for embedded console
    plugin = ConsolePlugin()
    plugin.start()  # patch

    view = ViewerWindow(filename="-", frameless=bool(port))
    view.show()
    if port:
        app.deferred_call(run_remote, app, view, filename, port, ref)
    else:
        app.deferred_call(run_local, app, view, filename, watch)
    app.start()
    log.debug("Viewer exited")


if __name__ == "__main__":
    main()
