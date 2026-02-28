import asyncio
import sys
from typing import Any, Optional, cast

import jsonpickle
from atom.api import Atom, Bool, Bytes, ContainerList, Dict, Instance, Int, Value
from enaml.application import deferred_call, timed_call

from declaracad.core.utils import log


class JsonRpcProtocol(Atom, asyncio.Protocol):
    #: Process transport
    transport = Value()

    #: ID count
    _id = Int()

    #: Holds responses temporarily
    _responses = Dict()

    #: Set when the protocol is ready
    connected = Bool(False)

    def invoke_method(self, method: str, *args, **kwargs) -> asyncio.Future[Any]:
        """Invoke the method with the attribute "on_{method}" on the remote
        connection.

        """
        if args and kwargs:
            raise ValueError("Can only use args or kwargs, not both")
        f: asyncio.Future[Any] = asyncio.Future()
        self._id += 1
        self._responses[self._id] = f
        self.send_message({"method": method, "params": args or kwargs, "id": self._id})
        return f

    def send_message(self, message: dict[str, Any], attempts: int = 10):
        if not self.connected:
            if attempts <= 0:
                log.error(f"Could not send message: {message} after several attempts")
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

    def line_received(self, line: str) -> Optional[asyncio.Future]:
        """Called when a newline is received

        Parameters
        ----------
        line: String
            The data

        """
        if not line:
            return None
        log.info(f"Received message '{line}'")
        try:
            request: dict[str, Any] = jsonpickle.loads(line)
        except Exception as e:
            return self.send_message(
                {
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f'Parse error: "{line}"',
                        "error": f"{e}",
                    },
                }
            )

        request_id: Optional[int] = request.get("id")
        method: Optional[str] = request.get("method")
        if method is None:
            if "error" in request:
                self.error_received(request_id, request["error"])
            elif "result" in request:
                self.result_received(request_id, request["result"])
            return None

        handler = getattr(self, f"on_{method}", None)
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

    def error_received(self, request_id: Optional[int], error: dict[str, Any]):
        """Standard error handler."""
        f = self._responses.pop(request_id, None)
        msg = str(error.get("message", ""))
        log.error("RemoteError: ")
        for line in msg.split("\n"):
            log.error(line)
        if f is not None:
            f.set_exception(RuntimeError(error))

    def result_received(self, request_id: Optional[int], result: Any):
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

    def write(self, message: str):
        self.protocol.invoke_method("print", message)

    def flush(self):
        pass


class ProcessLineReceiver(Atom, asyncio.SubprocessProtocol):
    """A process protocol that pushes output into a list of each line.
    Observe the `output` member in a view to have it update with live output.
    """

    #: Process transport
    process_transport = Instance(asyncio.SubprocessTransport)
    transport = Value()

    #: Status code
    exit_code = Int()

    #: Holds process output
    output = ContainerList()

    #: Redirect error to output
    err_to_out = Bool(True)

    #: Split on each line
    delimiter = Bytes(b"\n")

    def connection_made(self, transport: asyncio.BaseTransport):
        """Save a reference to the transports

        Parameters
        ----------
        transport: asyncio.SubprocessTransport
            The transport for stdin, stdout, and stderr pipes

        """
        process_transport = cast(asyncio.SubprocessTransport, transport)
        self.process_transport = process_transport
        self.transport = process_transport.get_pipe_transport(0)

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
            except ProcessLookupError:
                pass
