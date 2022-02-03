# -*- coding: utf-8 -*-
"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 13, 2017

@author: jrm
"""
import asyncio
import functools
import json
import os
import sys
import time
from asyncio.base_events import Server
from typing import TYPE_CHECKING, Iterator
from typing import List as ListType
from typing import Optional

import enaml
import jsonpickle
from atom.api import (Atom, Bool, Callable, ContainerList, Dict, Enum, Float,
                      ForwardInstance, ForwardTyped, Instance, Int, Property,
                      Str, Typed, observe, set_default)
from enaml.application import deferred_call, timed_call
from enaml.colors import ColorMember
from enaml.layout.api import InsertItem

from declaracad.core.api import Model, Plugin, log
from declaracad.core.utils import (JsonRpcProtocol, ProcessLineReceiver,
                                   get_bootstrap_cmd)
from declaracad.occ.shape import Part

if TYPE_CHECKING:
    from declaracad.editor.plugin import Document

    with enaml.imports():
        from .remote import ViewerDockItem


@functools.lru_cache
def is_remote_attr(name: str):
    """Check if the given attr name is valid on the remote viewer."""
    with enaml.imports():
        from .remote import ModelViewer, ViewerWindow
    attrs = [name]
    if name.startswith("set_"):
        attrs.append(name[4:])
    for cls in (ViewerWindow, ModelViewer):
        for attr in attrs:
            if hasattr(cls, attr):
                return True
    return False


def viewer_factory():
    with enaml.imports():
        from .remote import ViewerDockItem
    return ViewerDockItem


def remote_viewer():
    with enaml.imports():
        from .remote import RemoteViewer
    return RemoteViewer


def document_type():
    from declaracad.editor.plugin import Document

    return Document


class EmptyFileError(Exception):
    """This is raised when no source code is given such as when a new file
    is created but unsaved.
    """


class ModelExporter(Atom):
    """Interface for model exporters"""

    extension = ""
    path = Str()
    filename = Str()

    def _default_path(self):
        ext = self.extension.lower()
        filename = os.path.splitext(self.filename)[0]
        return "{}.{}".format(filename, ext)

    def export(self):
        """Export a DeclaraCAD model from an enaml file to a 3D model format
        with the given options.

        """
        raise NotImplementedError

    @classmethod
    def get_options_view(cls):
        """Return the options view used to define the paramters that can be
        used by this exporter.

        """
        raise NotImplementedError


class ScreenshotOptions(Atom):
    #: Path to save
    path = Str()

    #: Default save directory
    default_dir = Str()

    #: Document file name
    filename = Str()

    #: Only screenshot this view
    target = Str()

    def _default_path(self):
        path, filename = os.path.split(self.filename)
        default_dir = self.default_dir or path
        filename, ext = os.path.splitext(filename)
        return os.path.join(default_dir, "{}.png".format(filename))

    def format(self):
        """Return formatted option values for the exporter app to parse"""
        return json.dumps(self.__getstate__())


class ViewerAction(Atom):
    name = Str()
    key = Str()
    action = Callable()


class ViewerProcess(ProcessLineReceiver):
    #: Viewer instance
    viewer = ForwardTyped(viewer_factory)

    #: Process handle
    process = Instance(object)

    #: Server protocol
    protocol = ForwardTyped(lambda: RemoteViewerServerProtocol)

    #: Reference to the plugin
    plugin = ForwardTyped(lambda: ViewerPlugin)

    #: Document
    document = ForwardTyped(document_type)

    #: Rendering error
    errors = Str()

    #: Process terminated intentionally
    terminated = Bool(False)

    #: Count restarts so we can detect issues with startup s
    restarts = Int()

    #: Max number it will attempt to restart
    max_retries = Int(10)

    #: Capture stderr separately
    err_to_out = set_default(False)

    def redraw(self):
        if self.document:
            # Trigger a reload
            self.document.version += 1
        elif self.protocol:
            self.protocol.set("version", self._id)

    @observe("document")
    def _update_document(self, change):
        protocol = self.protocol
        if protocol is None:
            return
        name = self.document.name if self.document else "-"
        protocol.set("filename", name)

    @observe("document.version")
    def _update_version(self, change):
        protocol = self.protocol
        if protocol is None:
            return
        doc = self.document
        if doc is not None:
            protocol.set("version", doc.version)

    async def start(self):
        cmd = get_bootstrap_cmd()
        cmd.extend(
            ["view", "-", "--port", str(self.plugin.port), "--ref", self.viewer.name]
        )
        log.debug(f"Spawning '{' '.join(cmd)}'")
        loop = asyncio.get_event_loop()
        self.process = await loop.subprocess_exec(lambda: self, *cmd)
        return self.process

    def restart(self):
        self.restarts += 1

        if not self.plugin.port:
            # The server port is not available at startup until bound
            timed_call(100, self.restart)
            return

        # TODO: 100 is probably excessive
        if self.restarts > self.max_retries:
            plugin = self.plugin
            plugin.workbench.message_critical(
                "Viewer failed to start",
                "Could not get the viewer to start after several attempts.",
            )

            raise RuntimeError(
                "renderer | Failed to successfully start renderer aborting!"
            )

        log.debug(f"Attempting to restart remote viewer {self.viewer.name}")
        deferred_call(self.start)

    def connection_made(self, transport):
        super().connection_made(transport)
        self.terminated = False

    def err_received(self, data):
        """Catch and log error output attempting to decode it"""
        doc = self.document
        for line in data.split(b"\n"):
            if not line:
                continue
            if line.startswith(b"QWidget::") or line.startswith(b"QPainter::"):
                continue
            try:
                line = line.decode()
                log.debug(f"render | err | {line}")
                if doc:
                    doc.append_output(line)
            except Exception as e:
                log.exception(e)
                log.debug(f"render | err | {line}")

    def process_exited(self, reason=None):
        log.warning(f"renderer | process ended: {reason}")
        if not self.terminated:
            # Clear the filename on crash so it works when reset
            self.restart()
        log.warning("renderer | stdout closed")

    def terminate(self):
        if self.protocol:
            self.protocol.transport.close()
        self.terminated = True
        super().terminate()


class RemoteViewerServerProtocol(JsonRpcProtocol):
    """Protocol to talk with the remote viewer"""

    #: Window id obtained after starting the process
    window_id = Int()

    #: Reference to the Viewer plugin
    plugin = ForwardTyped(lambda: ViewerPlugin)

    #: Reference to the Viewer dock item
    dock_item = ForwardTyped(viewer_factory)

    #: Reference to the document
    document = Property(lambda s: s.dock_item.process.document if s.dock_item else None)

    # -------------------------------------------------------------------------
    # Remote viewer message handlers
    # -------------------------------------------------------------------------
    def connection_made(self, transport):
        self.transport = transport
        self.connected = True
        log.debug(f"Remote viewer connected {transport}")

    def connection_lost(self, err):
        self.connected = False
        self.window_id = 0
        log.debug(f"Remote viewer connection lost {err}")

    def set(self, attr, value):
        return self.invoke_method("set", attr, value)

    def call(self, method, *args, **kwargs):
        return self.invoke_method("call", method, *args, **kwargs)

    def on_welcome(self, viewer_name, window_id):
        dock_item = self.plugin.get_viewer(viewer_name)
        if dock_item is not None:
            # Save reference to which viewer this is
            self.dock_item = dock_item
            process = dock_item.process
            process.restarts = 0  # Reset
            process.protocol = self
            self.window_id = window_id
            log.debug(f"viewer {dock_item.name} connected!")

            # Set initial document
            doc = self.document
            if doc:
                self.set("filename", doc.name)

    def on_invoke_command(self, response):
        command_id = response.get("command_id")
        parameters = response.get("parameters", {})
        log.debug(f"viewer | out | {command_id}({parameters})")
        self.plugin.workbench.invoke_command(command_id, parameters)

    def on_render_error(self, response):
        if self.document:
            msg = response["error"]["message"].split("\n")
            self.document.errors.extend(msg)

    def on_render_success(self, response):
        if self.document:
            self.document.errors = []

    def on_print(self, message):
        m = message.strip()
        if m and self.document:
            self.document.append_output(m)

    def on_shape_selection(self, response):
        #: TODO: Do something with this?
        if self.document:
            self.document.append_output(str(response["result"]))

    def error_received(self, request_id, error):
        super().error_received(request_id, error)
        if self.document:
            msg = str(error.get("message", "") or error)
            self.document.append_output(msg)

    def unhandled_response(self, response):
        log.warning(f"Unhandled response: {response}")


class ViewerPlugin(Plugin):
    # -------------------------------------------------------------------------
    # Default viewer settings
    # -------------------------------------------------------------------------
    background_mode = Enum("gradient", "solid").tag(config=True, viewer="background")
    background_top = ColorMember("lightgrey").tag(config=True, viewer="background")
    background_bottom = ColorMember("grey").tag(config=True, viewer="background")
    background_fill_method = Enum(
        "corner3",
        "corner1",
        "corner2",
        "corner4",
        "ver",
        "hor",
        "diag1",
        "diag2",
    ).tag(config=True, viewer="background")
    trihedron_mode = Str("right-lower").tag(config=True, viewer=True)

    #: Defaults
    shape_color = ColorMember("steelblue").tag(config=True, viewer=True)

    #: Grid options
    grid_mode = Str().tag(config=True, viewer=True)
    grid_major_color = ColorMember("#444").tag(config=True, viewer="grid_colors")
    grid_minor_color = ColorMember("#888").tag(config=True, viewer="grid_colors")

    #: Rendering options
    antialiasing = Bool(True).tag(config=True, viewer=True)
    raytracing = Bool(True).tag(config=True, viewer=True)
    draw_boundaries = Bool(True).tag(config=True, viewer=True)
    shadows = Bool(True).tag(config=True, viewer=True)
    reflections = Bool(True).tag(config=True, viewer=True)
    chordial_deviation = Float(0.001).tag(config=True, viewer=True)

    #: Viewer units
    display_units = Enum("mm", "cm", "m", "in", "ft").tag(config=True, viewer=True)

    #: Viewer port
    port = Int()
    server = Instance(Server)

    def start(self):
        super().start()
        deferred_call(self.start_server)

    async def start_server(self):
        """Start a server to handle viewer connections"""
        loop = asyncio.get_event_loop()
        server = self.server = await loop.create_server(
            lambda: RemoteViewerServerProtocol(plugin=self), "127.0.0.1", 0
        )
        socket = server.sockets[0]
        ip, self.port = socket.getsockname()
        log.info(f"Server listening dcad://{ip}:{self.port}")

    # -------------------------------------------------------------------------
    # Plugin members
    # -------------------------------------------------------------------------
    #: Default dir for screenshots
    screenshot_dir = Str().tag(config=True)

    #: Exporters
    exporters = ContainerList()

    def get_viewer_members(self):
        for m in self.members().values():
            meta = m.metadata
            if not meta:
                continue
            if meta.get("viewer"):
                yield m

    def get_viewers(self) -> Iterator["ViewerDockItem"]:
        ViewerDockItem = viewer_factory()
        dock = self.workbench.get_plugin("declaracad.ui").get_dock_area()
        for item in dock.dock_items():
            if isinstance(item, ViewerDockItem):
                yield item

    def get_viewer(self, name: Optional[str] = None) -> Optional["ViewerDockItem"]:
        """Get the viewer with the given name"""
        for viewer in self.get_viewers():
            if name is None:
                return viewer
            elif viewer.name == name:
                return viewer

    def fit_all(self, event=None):
        return
        viewer = self.get_viewer()
        viewer.proxy.display.FitAll()

    def run(self, event=None):
        viewer = self.get_viewer()
        editor = self.workbench.get_plugin("declaracad.editor").get_editor()
        doc = editor.doc
        # viewer.set_source(editor.get_text())
        doc.version += 1

    def _default_exporters(self) -> ListType["ModelExporter"]:
        """TODO: push to an ExtensionPoint"""
        from declaracad.occ.exporters.iges.exporter import IgesExporter
        from declaracad.occ.exporters.step.exporter import StepExporter
        from declaracad.occ.exporters.stl.exporter import StlExporter
        from declaracad.occ.exporters.vrml.exporter import VrmlExporter

        return [IgesExporter, StlExporter, StepExporter, VrmlExporter]

    # -------------------------------------------------------------------------
    # Plugin commands
    # -------------------------------------------------------------------------
    def export(self, options):
        """Export the current model to stl"""
        if not options:
            raise ValueError("An export `options` parameter is required")

        # Pickle the configured exporter and send it over
        cmd = get_bootstrap_cmd()
        data = jsonpickle.dumps(options)
        assert data != "null", f"Exporter failed to serialize: {options}"
        cmd.extend(["export", data])
        log.debug(" ".join(cmd))
        protocol = ProcessLineReceiver()
        loop = asyncio.get_event_loop()
        deferred_call(loop.subprocess_exec, lambda: protocol, *cmd)
        return protocol

    def screenshot(self, options: Optional[ScreenshotOptions] = None):
        """Export the views as a screenshot"""
        if options is None:
            editor = self.workbench.get_plugin("declaracad.editor")
            filename = editor.active_document.name
            options = ScreenshotOptions(
                filename=filename, default_dir=self.screenshot_dir
            )
        else:
            # Update the default screenshot dir
            self.screenshot_dir, _ = os.path.split(options.path)
        results = []
        if options.target:
            viewer = self.get_viewer(options.target)
            if viewer:
                results.append(viewer.take_screenshot(options.path))
        else:
            for i, viewer in enumerate(self.get_viewers()):
                # Insert view number
                path, ext = os.path.splitext(options.path)
                filename = "{}-{}{}".format(path, i + 1, ext)
                results.append(viewer.take_screenshot(filename))
        return results

    def add_viewer(
        self,
        position: str = "right",
        target: str = "",
        document: Optional["Document"] = None,
    ):
        """Create a new viewer window and insert it into the dock area."""
        editor_plugin = self.workbench.get_plugin("declaracad.editor")
        dock = editor_plugin.get_dock_area()
        doc = document or editor_plugin.active_document

        ViewerDockItem = viewer_factory()
        item = ViewerDockItem(dock, plugin=self, document=doc)
        op = InsertItem(item=item.name, position=position, target=target)
        dock.update_layout(op)
