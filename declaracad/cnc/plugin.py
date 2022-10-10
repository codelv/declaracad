"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Aug 8, 2018

@author: jrm
"""
import asyncio
import time
import uuid
from typing import Union

import serial
from atom.api import Bool, Bytes, ContainerList, Enum, Float, Instance, Int, List, Str
from enaml.application import Application
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

    async def write(self, data: Union[str, bytes]):
        self.transport.write(data)

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
        self.connected = True
        self.connection.transport = transport

    def connection_lost(self, exc):
        self.connected = False
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
        # print(self.connection.transport.get_write_buffer_size())
        pass

    def resume_writing(self):
        # print(self.connection.transport.get_write_buffer_size())
        pass

    async def wait_until(self, fn, timeout=30, message="Timeout hit", rate=0.1):
        """Wait for the fn to return true or until the timeout hits

        Parameters
        ----------
        fn: Callable
            A function that returns a boolean when ready
        timeout: Float or None
            Time in seconds to wait before giving an error or None
            to block forever
        message: Str
            Message to set on the error if a timeout occurs
        rate: Float
            Time in seconds to wait before checking the fn again

        """
        start = time.time()
        while not fn():
            await asyncio.sleep(rate)
            if timeout is not None and (time.time() - start) > timeout:
                raise TimeoutError(message)

    # -------------------------------------------------------------------------
    # Device API
    # -------------------------------------------------------------------------
    async def connect(self):
        """Make the connection and wait until connection_made is called."""
        if self.connected:
            return
        await self.connection.connect(self)

        # Wait for it to connect
        await self.wait_until(lambda: self.connected, 30, message="Connection timeout")

    async def write(self, data: Union[str, bytes]):
        """Write the data and wait until the write buffer is empty.

        Parameters
        ----------
        data: Bytes or Str
            Data to write to the device

        """
        if not self.connected:
            return IOError("Not connected")
        if not isinstance(data, bytes):
            data = data.encode()

        # Manual flow control sleep until unpaused
        while self.paused and self.connected:
            await asyncio.sleep(0.001)
        if not self.connected:
            return IOError("Connection lost")

        self.last_write = data
        # Write just puts it into the write buffer
        # So wait until the buffer is empty (all written)
        # or the connection drops
        self.connection.transport.write(data)
        get_buffer_size = self.connection.transport.get_write_buffer_size
        await self.wait_until(
            lambda: not self.connected or get_buffer_size() == 0, timeout=None
        )
        if not self.connected:
            raise IOError("Connection dropped")

    async def disconnect(self):
        """Drop the connection. This will call connection_lost when it is
        actually closed.

        """
        if not self.connected:
            return
        await self.connection.disconnect()

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


class CncPlugin(Plugin):
    connection_types = [SerialConfig]

    #: Saved device devices
    devices = ContainerList(Device).tag(config=True)

    #: Active device device
    device = Instance(Device, ()).tag(config=True)

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
        if not device or device.busy:
            return
        device.busy = True
        rate = device.config.send_rate
        app = Application.instance()
        try:
            with open(filename, "rb") as f:
                await device.connect()
                for line in f:
                    if not device.connected:
                        raise IOError("Device disconnected")
                    if not device.busy:
                        raise RuntimeError("Send cancelled")
                    if rate:
                        await asyncio.sleep(rate)
                    app.process_events()
                    await device.write(line)

        finally:
            device.busy = False
