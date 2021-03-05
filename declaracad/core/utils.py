"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""
import io
import os
import sys
import asyncio
import logging
import functools
import traceback
import jsonpickle
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler

from atom.api import Atom, Value, Int, Bool, Bytes, ContainerList

from enaml.image import Image
from enaml.icon import Icon, IconImage
from enaml.application import Application, timed_call


# -----------------------------------------------------------------------------
# Logger
# -----------------------------------------------------------------------------
log = logging.getLogger("declaracad")


def clip(s, n=1000):
    """ Shorten the name of a large value when logging"""
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
    """ Load an icon from the res/icons folder using the name
    without the .png

    """
    path = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(path, 'res', 'icons', '%s.png' % name)


def load_image(name):
    """ Get and cache an enaml Image for the given icon name.

    """
    path = icon_path(name)
    global _IMAGE_CACHE
    if path not in _IMAGE_CACHE:
        with open(path, 'rb') as f:
            data = f.read()
        _IMAGE_CACHE[path] = Image(data=data)
    return _IMAGE_CACHE[path]


def load_icon(name):
    img = load_image(name)
    icg = IconImage(image=img)
    return Icon(images=[icg])


def menu_icon(name):
    """ Icons don't look good on Linux/osx menu's """
    if sys.platform == 'win32':
        return load_icon(name)
    return None


def format_title(docs, doc, path, unsaved):
    """ Attempt to format the title using the shortest unique name that
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
    duplicates = [d.name for d in docs
                    if d != doc and os.path.split(d.name)[-1] == name]

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


@contextmanager
def capture_output():
    _stdout = sys.stdout
    try:
        capture = io.StringIO()
        sys.stdout = capture
        yield capture
    finally:
        sys.stdout = _stdout


def process_events():
    """ Let the event loop process events

    """
    Application.instance()._qapp.processEvents()


def get_bootstrap_cmd():
    """ Get the command to the main executable depending on how it's run

    Returns
    -------
    cmd: List[str]
        The command to run declaracad
    """
    is_frozen = getattr(sys, "frozen", False)
    cmd = [sys.executable]
    if not sys.executable.endswith('declaracad') and not is_frozen:
        cmd.extend(['-m', 'declaracad'])
    return cmd


class JSONRRCProtocol(Atom, asyncio.Protocol):
    #: Process transport
    transport = Value()

    def send_message(self, message):
        response = {'jsonrpc': '2.0'}
        response.update(message)
        encoded_msg = jsonpickle.dumps(response).encode()+b'\r\n'
        self.transport.write(encoded_msg)

    def data_received(self, data):
        """ Process stdin as json-rpc request

        Parameters
        ----------
        data: Bytes
            The data received from stdin.

        """
        # TODO: Handle partial reads
        for line in data.split(b'\n'):
            self.line_received(line.decode())

    def line_received(self, line):
        """ Called when a newline is received

        Parameters
        ----------
        line: String
            The data

        """
        if not line:
            return
        try:
            request = jsonpickle.loads(line)
        except Exception as e:
            return self.send_message({'id': None, 'error': {
                'code': -32700, 'message': f'Parse error: "{line}"'}})

        request_id = request.get('id')
        method = request.get('method')
        if method is None:
            return self.send_message({"id": request_id, "error": {
                'code': -32600, 'message': "Invalid request"}})

        handler = getattr(self, 'handle_{}'.format(method), None)
        if handler is None:
            msg = f"Method '{method}' not found"
            return self.send_message({"id": request_id, 'error': {
                'code': -32601, 'message': msg}})

        try:
            params = request.get('params', [])
            if isinstance(params, dict):
                result = handler(**params)
            else:
                result = handler(*params)
            return self.send_message({'id': request_id, 'result': result})
        except Exception as e:
            return self.send_message({"id": request_id, 'error': {
                'code': -32500, 'message': traceback.format_exc()}})


class ProcessLineReceiver(Atom, asyncio.SubprocessProtocol):
    """ A process protocol that pushes output into a list of each line.
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
    delimiter = Bytes(b'\n')

    def connection_made(self, transport):
        """ Save a reference to the transports

        Parameters
        ----------
        transport: asyncio.SubprocessTransport
            The transport for stdin, stdout, and stderr pipes

        """
        self.process_transport = transport
        self.transport = transport.get_pipe_transport(0)

    def pipe_data_received(self, fd, data):
        """ Forward calls to data_received or err_received based one the fd

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

    def data_received(self, data):
        """ Called for stdout data and stderr data if err_to_out is True

        Parameters
        ----------
        data: Bytes
            The data received

        """
        self.output.append(data)

    def err_received(self, data):
        """ Called for stderr data if err_to_out is set to False

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
