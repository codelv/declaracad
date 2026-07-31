"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 8, 2018

@author: jrm
"""

import asyncio
import uuid
from typing import Union

import serial
from atom.api import (
    Atom,
    Bool,
    Bytes,
    ContainerList,
    Enum,
    Float,
    Instance,
    Int,
    List,
    Str,
    observe,
)
from serial.tools.list_ports import comports

from declaracad.core.api import Model, Plugin, log
from declaracad.core.serial import SerialTransport, create_serial_connection
from declaracad.occ.api import Point

from . import gcode


class TimeoutError(Exception):
    pass


class Connection(Model):
    def get_connections(self):
        """Do a scan to see which devices are available."""
        raise NotImplementedError

    async def connect(self, protocol: asyncio.Protocol):
        """Make the connection"""
        raise NotImplementedError

    async def write(self, data: Union[str, bytes]):
        """Write data to the connection"""
        raise NotImplementedError

    async def disconnect(self):
        """Close the connection"""
        raise NotImplementedError


class SerialConfig(Model):
    #: Available serial ports
    ports = List()

    PARITIES = {v: k for k, v in serial.PARITY_NAMES.items()}

    #: Serial port config
    port = Str().tag(config=True)
    baudrate = Int(115200).tag(config=True)
    bytesize = Enum(
        serial.EIGHTBITS, serial.SEVENBITS, serial.SIXBITS, serial.FIVEBITS
    ).tag(config=True)
    parity = Enum(*serial.PARITY_NAMES.values()).tag(config=True)
    stopbits = Enum(
        serial.STOPBITS_ONE, serial.STOPBITS_ONE_POINT_FIVE, serial.STOPBITS_TWO
    ).tag(config=True)
    xonxoff = Bool().tag(config=True)
    rtscts = Bool(True).tag(config=True)
    dsrdtr = Bool().tag(config=True)

    def _default_ports(self):
        return comports()

    def _default_parity(self):
        return "None"

    def _default_port(self):
        if self.ports:
            return self.ports[0].device
        return ""

    def refresh(self):
        self.ports = self._default_ports()


class SerialConnection(Connection):
    """A connection implementation for Serial ports."""

    handle = Instance(object)
    config = Instance(SerialConfig, ()).tag(config=True)
    transport = Instance(SerialTransport)
    pending_write = Instance(asyncio.Future)

    @classmethod
    def get_connections(cls):
        connections = []
        for port in comports():
            conn = cls(config=SerialConfig(port=port.device))
            connections.append(conn)
        return connections

    async def connect(self, protocol: asyncio.Protocol):
        if self.handle is not None:
            transport, _ = self.handle
            transport.close()
        loop = asyncio.get_event_loop()

        config = self.config
        self.handle = await create_serial_connection(
            loop,
            lambda: protocol,
            config.port,
            baudrate=config.baudrate,
            bytesize=config.bytesize,
            parity=SerialConfig.PARITIES[config.parity],
            stopbits=config.stopbits,
            xonxoff=config.xonxoff,
            rtscts=config.rtscts,
        )
        # This is a patched in function in declaracad/core/serial.py
        transport = self.handle[0]
        transport._wrote_callback = self.on_write_complete

    def on_write_complete(self, data: bytes):
        # This is invoked in SerialTransport._write_data
        future = self.pending_write
        if future and not future.done():
            if not data:
                future.set_result(False)  # failed
            elif self.transport.get_write_buffer_size() == 0:
                future.set_result(True)  # complete
            # else not done

    async def write(self, data: Union[str, bytes]) -> bool:
        if future := self.pending_write:
            await future
        try:
            loop = asyncio.get_event_loop()
            future = self.pending_write = loop.create_future()
            # Write just puts it into the write buffer
            # So wait until the buffer is empty (all written)
            # or the connection drops
            self.transport.write(data)
            return await future
        finally:
            self.pending_write = None

    async def disconnect(self):
        if self.transport:
            self.transport.close()


class DeviceConfig(Model):
    #: Send rate
    send_rate = Float(strict=False).tag(config=True)

    #: Units
    units = Enum("", "mm", "in").tag(config=True)

    #: Output scale
    scale_x = Float(1.0, strict=False).tag(config=True)
    scale_y = Float(1.0, strict=False).tag(config=True)
    scale_z = Float(1.0, strict=False).tag(config=True)

    #: Mirror Z output
    mirror_x = Bool().tag(config=True)
    mirror_y = Bool().tag(config=True)
    mirror_z = Bool().tag(config=True)

    #: Swap XY output
    swap_xy = Bool().tag(config=True)

    #: Preceision when outputting gcode
    PRECISIONS = {
        "maximum": None,
        "integer": 0,
        "1": 1,
        "2": 2,
        "3": 3,
        "4": 4,
        "5": 5,
        "6": 6,
        "7": 7,
        "8": 8,
        "9": 9,
    }

    precision = Enum(*PRECISIONS.keys()).tag(config=True)

    #: Origin position relative to model origin
    origin = Instance(Point, ()).tag(config=True)

    #: Commands sent before a job
    init_commands = Str().tag(config=True)

    #: Commands sent after a job
    finalize_commands = Str().tag(config=True)

    #: Manually throttle output based on xon/xoff
    manual_flow_control = Bool().tag(config=True)


class Device(Model, asyncio.Protocol):
    #: Name
    name = Str().tag(config=True)

    #: UUID
    uuid = Str().tag(config=True)

    #: Default
    default = Bool().tag(config=True)

    #: Device state
    connected = Bool()
    busy = Bool()
    paused = Bool()
    last_read = Bytes()
    last_write = Bytes()
    errors = Str()

    #: Config
    config = Instance(DeviceConfig, ()).tag(config=True)

    #: The connection
    connection = Instance(Connection).tag(config=True)

    def _default_uuid(self):
        return str(uuid.uuid4().hex)

    def __hash__(self):
        return int(self.uuid, 16)

    def __eq__(self, other):
        if not isinstance(other, Device):
            return False
        return self.uuid == other.uuid

    def _observe_paused(self, change):
        log.debug("{} {}".format(self.name, "paused" if self.paused else "resumed"))

    # -------------------------------------------------------------------------
    # Protocol API
    # -------------------------------------------------------------------------
    def connection_made(self, transport):
        self.connection.transport = transport
        self.connected = True
        self.paused = False

    def connection_lost(self, exc):
        self.connected = False
        self.paused = False
        self.errors = f"{exc}"

    def data_received(self, data: bytes):
        if self.config.manual_flow_control:
            for c in data:
                if c == 0x13:
                    self.paused = True
                elif c == 0x11:
                    self.paused = False

        self.last_read = data

    def pause_writing(self):
        self.paused = True

    def resume_writing(self):
        self.paused = False

    # -------------------------------------------------------------------------
    # Device API
    # -------------------------------------------------------------------------
    async def connect(self, timeout: float = 30):
        """Make the connection and wait until connection_made is called."""
        if self.connected:
            return
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.observe("connected", future.set_result)
        try:
            await self.connection.connect(self)
            await asyncio.wait_for(future, timeout)
        finally:
            self.unobserve("connected", future.set_result)

    async def write(self, data: Union[str, bytes]):
        """Write the data and wait until the write buffer is empty.

        Parameters
        ----------
        data: Bytes or Str
            Data to write to the device

        """
        if not isinstance(data, bytes):
            data = data.encode()

        # Manual flow control sleep until unpaused
        if self.paused:
            loop = asyncio.get_event_loop()
            future = loop.create_future()
            self.observe("paused", future.set_result)
            try:
                await future
            finally:
                self.unobserve("paused", future.set_result)
        if not self.connected:
            return IOError("Connection lost")

        self.last_write = data
        await self.connection.write(data)

    async def disconnect(self, timeout: float = 0):
        """Drop the connection. This will call connection_lost when it is
        actually closed.

        """
        if not self.connected:
            return
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self.observe("connected", future.set_result)
        try:
            await self.connection.disconnect()
            await asyncio.wait_for(future, timeout)
        finally:
            self.unobserve("connected", future.set_result)

    def convert(self, point: Point):
        """Convert a point based on this device's configuration

        Parameters
        ----------
        point: declaracad.occ.shape.Point
            The point to convert

        Returns
        -------
        converted_point: Tuple
            Tuple of converted values

        """
        config = self.config
        precision = config.PRECISIONS.get(config.precision)
        o = config.origin
        x = o.x - point.x if config.mirror_x else point.x - o.x
        y = o.y - point.y if config.mirror_y else point.y - o.y
        z = o.z - point.z if config.mirror_z else point.z - o.z
        x = gcode.convert(x, config.scale_x, precision, config.units)
        y = gcode.convert(y, config.scale_y, precision, config.units)
        z = gcode.convert(z, config.scale_z, precision, config.units)
        if config.swap_xy:
            x, y = y, x
        return (x, y, z)

    async def rapid_move_to(self, point: Point):
        """Send a G0 to the point"""
        x, y, z = self.convert(point)
        await self.write(f"G0 X{x} Y{y} Z{z}\n")


class Job(Atom):
    """Tracks sending a file to a device"""

    filename = Str()
    progress = Float()
    status = Enum("ready", "running", "paused", "aborted", "complete")
    start_line = Int()
    current_line = Int()
    line_count = Int()

    def abort(self):
        if self.status not in ("running", "paused"):
            raise RuntimeError(f"Cannot abort job in '{self.status}' state")
        self.status = "aborted"

    @observe("line_count", "current_line")
    def _update_progress(self, change):
        if self.line_count > 0:
            self.progress = max(0, min(100, self.current_line / self.line_count * 100))

    async def run(self, device: Device):
        rate = device.config.send_rate

        if self.status not in ("ready", "aborted", "complete"):
            raise RuntimeError("Cannot run a running job")
        self.status = "running"
        start_line = self.start_line
        with open(self.filename, "rb") as f:
            # Count lines
            line_count = 0
            for line in f:
                line_count += 1
            self.line_count = line_count
            self.current_line = 0
            f.seek(0)

            await device.connect()

            for line in f:
                if self.status == "aborted":
                    break
                self.current_line += 1
                if self.current_line < start_line:
                    continue
                if not device.connected:
                    raise IOError("Device disconnected")
                if not device.busy:
                    raise RuntimeError("Send cancelled")
                await asyncio.sleep(rate)
                await device.write(line)

            # If not aborted
            if self.status == "running":
                self.status = "complete"


class CncPlugin(Plugin):
    connection_types = [SerialConfig]

    #: Saved device devices
    devices = ContainerList(Device).tag(config=True)

    #: Active device device
    device = Instance(Device, ()).tag(config=True)

    #: Job
    job = Instance(Job).tag(config=False)

    #: Monitor fields
    add_newline = Bool(False).tag(config=True)
    strip_whitespace = Bool(False).tag(config=True)
    input_enabled = Bool(True).tag(config=True)
    output_enabled = Bool(True).tag(config=True)
    autoscroll = Bool(True).tag(config=True)

    #: Command history
    history = ContainerList().tag(config=True)

    def _default_device(self):
        if not self.devices:
            dev = Device(name="New device", connection=SerialConnection(), default=True)
            self.devices = [dev]
        # Try to get the first default device (ideally only one should exist)
        for d in self.devices:
            if d.default:
                return d
        # If no default is set fallback to the first device
        return self.devices[0]

    def add_device(self):
        """Create a new device"""
        conn = Device(name="New device", connection=SerialConnection())
        devices = self.devices[:]
        devices.append(conn)
        self.device = conn
        self.devices = devices

    def remove_device(self, device: Device):
        if device in self.devices and len(self.devices) > 1:
            devices = self.devices[:]
            devices.remove(device)
            self.device = devices[0]
            self.devices = devices

    def set_default_device(self, device: Device):
        for d in self.devices:
            d.default = d == device

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------
    async def connect(self):
        if self.device:
            await self.device.connect()

    async def disconnect(self):
        if self.device:
            await self.device.disconnect()

    async def rapid_move_to(self, point: Point):
        """Send a rapid move to command to the given point if the device
        is connected and not in use.

        Parameters
        ----------
        point: Point or 3 item tuple
            The position to move to

        """
        device = self.device
        if device and not device.busy:
            if not device.connected:
                await device.connect()
            await device.rapid_move_to(point)

    async def send_file(self, filename: str):
        """Send a file to the device line by line

        Parameters
        ----------
        filename: Str
            The path to the file
        """
        device = self.device
        job = self.job
        if not device or device.busy or (job and job.status == "running"):
            return
        device.busy = True
        try:
            job = self.job = Job(filename=filename)
            await job.run(device)
        finally:
            device.busy = False
