"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 24, 2020

@author: jrm
"""

import asyncio
import logging
import os
import signal
import sys
from inspect import iscoroutinefunction
from typing import Any, Callable, Optional

from asyncqtpy import QEventLoop, QEventLoopPolicy
from atom.api import Bool, Instance, Typed
from enaml.qt import QT_API
from enaml.qt.qt_application import QtApplication
from enaml.qt.QtCore import Qt, QTimer
from enaml.qt.QtWidgets import QApplication

from declaracad.core.utils import log


def init_qapp(platform: Optional[str] = None):
    """Initialize the QApplication and configure the platform and library paths.

    Parameters
    ----------
    platform: str | None
        Specifies the Qt platform unless QT_QPA_PLATFORM is defined. This is unused on windows.

    """
    args = ["declaracad"]
    if sys.platform == "win32":
        QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)
    elif "QT_QPA_PLATFORM" not in os.environ and platform is not None:
        # Set platform to xcb on linux. OCCT does not yet support wayland
        args.append("-platform")
        args.append(platform)

    is_frozen = getattr(sys, "frozen", False)
    if is_frozen:
        # Workaround an issue with frozen Qt not properly loading plugins
        if "side" in QT_API:
            from PySide6 import QtCore
        else:
            from PyQt6 import QtCore
        qt_lib_dir = os.path.dirname(QtCore.__file__)
        plugins_dir = os.path.join(qt_lib_dir, "plugins")
        QApplication.addLibraryPath(plugins_dir)

    log.debug(f"QApp init {args}")
    return QApplication(args)


class Application(QtApplication):
    """ """

    interp_timer = Typed(QTimer)

    def __init__(self, platform: Optional[str] = None):
        init_qapp(platform)
        super().__init__()
        self.init_sigint()

    def init_sigint(self):
        """Add sigint handler"""
        signal.signal(signal.SIGINT, lambda sig, frame: self.stop())
        # Timer makes it close with Ctrl+C without needing focus/click
        # See https://stackoverflow.com/questions/4938723/
        timer = self.interp_timer = QTimer()
        timer.timeout.connect(lambda: None)
        timer.start(500)

    def stop(self):
        """Stop the application"""
        log.debug("App stopped")
        super().stop()

    def process_events(self):
        """Let the the app process events during long-running cpu intensive
        tasks.

        """
        self._qapp.processEvents()


class AsyncApplication(Application):
    """Add asyncio support . Seems like a complete hack compared to twisted
    but whatever.

    """

    loop = Instance(QEventLoop, factory=asyncio.get_event_loop)
    queue = Instance(asyncio.Queue, ())
    running = Bool()

    def __init__(self, platform: Optional[str] = None):
        super().__init__(platform)
        asyncio.set_event_loop_policy(QEventLoopPolicy())
        assert self.loop is not None

        # Set logger level
        for name in logging.root.manager.loggerDict:
            if name.startswith("asyncqt"):
                log = logging.getLogger(name)
                log.setLevel(logging.WARN)

    def start(self):
        """Run using the event loop"""
        log.info("Application starting")
        self.running = True
        loop = self.loop
        loop.set_exception_handler(self.on_async_exception)
        try:
            with loop:
                loop.run_until_complete(self.main())
        except RuntimeError as e:
            if "loop stopped" not in f"{e}":
                raise
        finally:
            self.running = False

    def stop(self):
        """Stop the application"""
        self.running = False
        self.queue.put_nowait(None)
        super().stop()

    async def main(self):
        """Run any async deferred calls in the main ui loop."""
        while self.running:
            task = await self.queue.get()
            if task is None:
                break
            await task
        log.debug("Main finished")

    def on_async_exception(self, loop, context):
        """Exception handler that ignores"""
        return loop.default_exception_handler(context)

    def deferred_call(self, callback: Callable, *args: Any, **kwargs: Any):
        """Invoke a callable on the next cycle of the main event loop
        thread.

        Parameters
        ----------
        callback : callable
            The callable object to execute at some point in the future.

        args, kwargs
            Any additional positional and keyword arguments to pass to
            the callback.

        """
        if iscoroutinefunction(callback) or kwargs.pop("async_", None):

            async def deferred_task():
                task = self.loop.create_task(callback(*args, **kwargs))
                await self.queue.put(task)

            return self.queue.put_nowait(deferred_task())
        return super().deferred_call(callback, *args, **kwargs)

    def timed_call(self, ms: float, callback: Callable, *args: Any, **kwargs: Any):
        """Invoke a callable on the main event loop thread at a
        specified time in the future.

        Parameters
        ----------
        ms : int
            The time to delay, in milliseconds, before executing the
            callable.

        callback : callable
            The callable object to execute at some point in the future.

        args, kwargs
            Any additional positional and keyword arguments to pass to
            the callback.

        """
        if iscoroutinefunction(callback) or kwargs.pop("async_", None):

            async def deferred_task():
                task = self.loop.create_task(callback(*args, **kwargs))
                await self.queue.put(task)

            return super().timed_call(ms, self.queue.put_nowait, deferred_task())
        return super().timed_call(ms, callback, *args, **kwargs)
