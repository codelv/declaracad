"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""
import asyncio
import functools
import logging
import os
import sys
import time
import traceback
from contextlib import contextmanager

import jsonpickle
from atom.api import (Atom, Bool, Bytes, ContainerList, Dict, Instance, Int,
                      Value)
from enaml.application import Application, timed_call
from enaml.icon import Icon, IconImage
from enaml.image import Image

# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
log = logging.getLogger("declaracad")


def clip(s, n=1000):
    """Shorten the name of a large value when logging"""
    v = str(s)
    if len(v) > n:
        v[:n] + "..."
    return v


# -----------------------------------------------------------------------------
# Icon and Image helpers
# -----------------------------------------------------------------------------
#: Cache for icons
_IMAGE_CACHE = {}


def icon_path(name):
    """Load an icon from the res/icons folder using the name
    without the .png

    """
    path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(path, "res", "icons", "%s.png" % name)


def load_image(name):
    """Get and cache an enaml Image for the given icon name."""
    path = icon_path(name)
    global _IMAGE_CACHE
    if path not in _IMAGE_CACHE:
        with open(path, "rb") as f:
            data = f.read()
        _IMAGE_CACHE[path] = Image(data=data)
    return _IMAGE_CACHE[path]


def load_icon(name):
    img = load_image(name)
    icg = IconImage(image=img)
    return Icon(images=[icg])


def menu_icon(name):
    """Icons don't look good on Linux/osx menu's"""
    if sys.platform == "win32":
        return load_icon(name)
    return None


def format_title(docs, doc, path, unsaved):
    """Attempt to format the title using the shortest unique name that
    does not conflict with any other opened documents.

    Based on Intellij's naming styles
    """
    if not path:
        unamed = [d for d in docs if not d.name]
        if doc in unamed:
            return "Untitled-%s*" % (unamed.index(doc) + 1)
        return "Untitled*"
    path, name = os.path.split(path)

    #: Find any others with the same name
    duplicates = [
        d.name for d in docs if d != doc and os.path.split(d.name)[-1] == name
    ]

    #: Add folders until it becomes unique we run out of folders
    if duplicates:
        sep = os.path.sep
        parts = path.split(sep)
        for i in reversed(range(len(parts))):
            tmp_name = sep.join(parts[i:])

            #: See if there's still duplicates
            duplicates = [d for d in duplicates if d.endswith(tmp_name)]
            if not duplicates:
                name = os.path.join(tmp_name, name)
                break

        #: Give up
        if duplicates:
            name += "({})".format(len(duplicates))

    if unsaved:
        name += "*"
    return name


def process_events():
    """Let the event loop process events"""
    Application.instance()._qapp.processEvents()


def get_bootstrap_cmd():
    """Get the command to the main executable depending on how it's run

    Returns
    -------
    cmd: List[str]
        The command to run declaracad
    """
    is_frozen = getattr(sys, "frozen", False)
    cmd = [sys.executable]
    if not sys.executable.endswith("declaracad") and not is_frozen:
        cmd.extend(["-m", "declaracad"])
    return cmd


@contextmanager
def log_time(start_message: str, done_message: str = "Done! ({} s)"):
    log.debug(start_message)
    t = time.time()
    yield
    log.debug(done_message.format(round((time.time() - t), 2)))


class JsonRpcProtocol(Atom, asyncio.Protocol):
    #: Process transport
    transport = Value()

    #: ID count
    _id = Int()

    #: Holds responses temporarily
    _responses = Dict()

    #: Set when the protocol is ready
    connected = Bool(False)

    def invoke_method(self, method, *args, **kwargs) -> asyncio.Future:
        """Invoke the method with the attribute "on_{method}" on the remote
        connection.

        """
        if args and kwargs:
            raise ValueError("Can only use args or kwargs, not both")
        f = asyncio.Future()
        self._id += 1
        self._responses[self._id] = f
        self.send_message({"method": method, "params": args or kwargs, "id": self._id})
        return f

    def send_message(self, message: dict, attempts: int = 10):
        if not self.connected:
            if attempts <= 0:
                log.error(
                    f"Could not send message: {message} " f"after several attempts"
                )
                return
            log.debug(f"Note: Message delayed {self}: {message}")
            timed_call(1000, self.send_message, message, attempts - 1)
            return
        log.debug(message)
        encoded_msg = jsonpickle.dumps(message).encode()
        self.transport.write(encoded_msg + b"\r\n")

    def data_received(self, data: bytes):
        """Process stdin as json-rpc request

        Parameters
        ----------
        data: Bytes
            The data received from stdin.

        """
        # TODO: Handle partial reads
        for line in data.split(b"\n"):
            self.line_received(line.decode())

    def line_received(self, line: str):
        """Called when a newline is received

        Parameters
        ----------
        line: String
            The data

        """
        if not line:
            return
        log.debug(f"Received message '{line}'")
        try:
            request = jsonpickle.loads(line)
        except Exception as e:
            return self.send_message(
                {
                    "id": None,
                    "error": {"code": -32700, "message": f'Parse error: "{line}"'},
                }
            )

        request_id = request.get("id")
        method = request.get("method")
        if method is None:
            if "error" in request:
                self.error_received(request_id, request["error"])
            elif "result" in request:
                self.result_received(request_id, request["result"])
            return

        handler = getattr(self, "on_{}".format(method), None)
        if handler is None:
            msg = f"Method '{method}' not found"
            return self.send_message(
                {"id": request_id, "error": {"code": -32601, "message": msg}}
            )

        try:
            params = request.get("params", [])
            if isinstance(params, dict):
                result = handler(**params)
            else:
                result = handler(*params)
            return self.send_message({"id": request_id, "result": result})
        except Exception as e:
            log.exception(e)
            return self.send_message(
                {
                    "id": request_id,
                    "error": {"code": -32500, "message": traceback.format_exc()},
                }
            )

    def error_received(self, request_id, error):
        """Standard error handler."""
        f = self._responses.pop(request_id, None)
        msg = str(error.get("message", ""))
        log.error("RemoteError: ")
        for line in msg.split("\n"):
            log.error(line)
        if f is not None:
            f.set_exception(RuntimeError(error))

    def result_received(self, request_id, result):
        """Standard response handler."""
        f = self._responses.pop(request_id, None)
        if f is not None:
            f.set_result(result)


class RemoteLogger(Atom):
    """Redirects stdout to the given protocol"""

    protocol = Instance(JsonRpcProtocol)

    #: Original stderr and stdout
    stdout = Value()
    stderr = Value()

    def attach(self):
        sys.stderr = sys.stdout = self

    def detach(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def write(self, message):
        self.protocol.invoke_method("print", message)

    def flush(self):
        pass


class ProcessLineReceiver(Atom, asyncio.SubprocessProtocol):
    """A process protocol that pushes output into a list of each line.
    Observe the `output` member in a view to have it update with live output.
    """

    #: Process transport
    process_transport = Value()
    transport = Value()

    #: Status code
    exit_code = Int()

    #: Holds process output
    output = ContainerList()

    #: Redirect error to output
    err_to_out = Bool(True)

    #: Split on each line
    delimiter = Bytes(b"\n")

    def connection_made(self, transport):
        """Save a reference to the transports

        Parameters
        ----------
        transport: asyncio.SubprocessTransport
            The transport for stdin, stdout, and stderr pipes

        """
        self.process_transport = transport
        self.transport = transport.get_pipe_transport(0)

    def pipe_data_received(self, fd: int, data: bytes):
        """Forward calls to data_received or err_received based one the fd

        Parameters
        ----------
        fd: Int
            The fd of the pipe
        data: Bytes
            The data received

        """
        if fd == 1:
            self.data_received(data)
        elif fd == 2:
            if self.err_to_out:
                self.data_received(data)
            else:
                self.err_received(data)

    def data_received(self, data: bytes):
        """Called for stdout data and stderr data if err_to_out is True

        Parameters
        ----------
        data: Bytes
            The data received

        """
        self.output.append(data)

    def err_received(self, data: bytes):
        """Called for stderr data if err_to_out is set to False

        Parameters
        ----------
        data: Bytes
            The data received

        """
        self.output.append(data)

    def terminate(self):
        if self.process_transport:
            try:
                self.process_transport.terminate()
            except ProcessLookupError as e:
                pass
