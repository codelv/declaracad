"""
Copyright (c) 2020, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 24, 2020

@author: jrm
"""
import asyncio
import inspect
import logging
import warnings
from queue import Empty, Queue

try:
    import nest_asyncio

    nest_asyncio.apply()
except ImportError as e:
    warnings.warn(f"Nest asyncio not found: {e}")

from asyncqtpy import QEventLoop, QEventLoopPolicy
from atom.api import Bool, Instance
from enaml.qt.qt_application import QtApplication

from declaracad.core.utils import log
from declaracad.fea.impl import fea_factories  # noqa: F401
from declaracad.occ.impl import occ_factories  # noqa: F401
from declaracad.viewer.qt import qt_factories  # noqa: F401

asyncio.set_event_loop_policy(QEventLoopPolicy())


class Application(QtApplication):
    """Add asyncio support . Seems like a complete hack compared to twisted
    but whatever.

    """

    loop = Instance(QEventLoop, factory=asyncio.get_event_loop)
    queue = Instance(Queue, ())
    running = Bool()

    def __init__(self):
        super().__init__()
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
        super().stop()

    async def main(self):
        """Run any async deferred calls in the main ui loop."""
        while self.running:
            try:
                task = self.queue.get(block=False)
                await task
            except Empty:
                await asyncio.sleep(0.1)
            # except Exception as e:
            #    log.exception(e)

    def on_async_exception(self, loop, context):
        """Exception handler that ignores"""
        # HACK: Ignore this error, Qt works, shut up
        # msg = context.get("exception")
        # if "cannot enter context" in str(msg):
        #    return
        return loop.default_exception_handler(context)

    def process_events(self):
        """Let the the app process events during long-running cpu intensive
        tasks.

        """
        self._qapp.processEvents()

    def deferred_call(self, callback, *args, **kwargs):
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
        if inspect.iscoroutinefunction(callback) or kwargs.pop("async_", None):
            task = asyncio.create_task(callback(*args, **kwargs))
            return self.add_task(task)
        return super().deferred_call(callback, *args, **kwargs)

    def timed_call(self, ms, callback, *args, **kwargs):
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
        if inspect.iscoroutinefunction(callback) or kwargs.pop("async_", None):
            task = asyncio.create_task(callback(*args, **kwargs))
            return super().timed_call(ms, self.add_task, task)
        return super().timed_call(ms, callback, *args, **kwargs)

    def add_task(self, task):
        """Put a task into the queue"""
        self.queue.put(task)
