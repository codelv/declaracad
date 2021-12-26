import os
import sys
import asyncio


async def create_stdio_connection(loop, protocol, limit=asyncio.streams._DEFAULT_LIMIT):
    loop = loop or asyncio.get_event_loop()
    if sys.platform == "win32":
        transport = _win32_stdio(protocol, loop)
    else:
        transport = await _unix_stdio(protocol, limit, loop)
    return transport, protocol


async def _unix_stdio(protocol, limit, loop):
    write_transport, write_protocol = await loop.connect_write_pipe(
        lambda: asyncio.streams.FlowControlMixin(loop=loop),
        os.fdopen(sys.stdout.fileno(), "wb"),
    )
    writer = asyncio.streams.StreamWriter(write_transport, write_protocol, None, loop)
    protocol.transport = writer
    reader = await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return reader, writer


def _win32_stdio(protocol, loop):
    class Win32StdinReader:
        def __init__(self):
            self.stdin = sys.stdin.buffer

        async def readline(self):
            # a single call to sys.stdin.readline() is thread-safe
            return await loop.run_in_executor(None, self.stdin.readline)

    class Win32StdoutWriter:
        def __init__(self):
            self.buffer = []
            self.stdout = sys.stdout.buffer

        def write(self, data):
            self.buffer.append(data)

        async def drain(self):
            data, self.buffer = self.buffer, []
            # a single call to sys.stdout.writelines() is thread-safe
            return await loop.run_in_executor(None, sys.stdout.writelines, data)

    return Win32StdinReader(), Win32StdoutWriter()
