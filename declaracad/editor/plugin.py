"""
Copyright (c) 2017-2026, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.
"""

import asyncio
import os
import subprocess
import sys
from typing import Optional, Union

import enaml
from atom.api import (
    Bool,
    ContainerList,
    Dict,
    Enum,
    ForwardTyped,
    Instance,
    Int,
    List,
    Range,
    Str,
    Tuple,
    Typed,
    observe,
)
from enaml.application import deferred_call, timed_call
from enaml.layout.api import InsertItem, InsertTab, RemoveItem
from enaml.scintilla.mono_font import MONO_FONT
from enaml.workbench.core.execution_event import ExecutionEvent

from declaracad.core.api import Model, Plugin, log
from declaracad.core.protocol import JsonRpcProtocol, ProcessLineReceiver
from declaracad.core.utils import get_bootstrap_cmd, source_hash

from .parsers import Outline, ParseResult
from .qt import qt_factories  # noqa: F401
from .syntaxes import SYNTAXES
from .themes import THEMES
from .widgets import CodeEditorIndicator

EXAMPLE_FILE = """# Created in DeclaraCAD
from declaracad.occ.api import *

enamldef Assembly(Part):
    Axis:
        pass
    Cut:
        color = 'blue'
        transparency = 0.8
        Box: box:
            dx = 50
            dy = 60
            dz = 10
        Looper:
            attr offset = 8
            iterable = [
                (box.x+offset, box.y+offset),
                (box.x+box.dx-offset, box.y+offset),
                (box.x+box.dx-offset, box.y+box.dy-offset),
                (box.x+offset, box.y+box.dy-offset),
            ]
            Hole:
                diameter = 5
                position = loop.item
                depth = box.dz
                far_edge = ("cone", 0.5)

"""

NEW_FILE_SOURCE = """# Created in DeclaraCAD
from declaracad.occ.api import *

enamldef Assembly(Part):
    Box:
        pass
"""


def editor_item_factory():
    with enaml.imports():
        from .view import EditorDockItem
    return EditorDockItem


def create_editor_item(*args, **kwargs):
    EditorDockItem = editor_item_factory()
    return EditorDockItem(*args, **kwargs)


def format_title(
    docs: list["Document"], doc: "Document", path: str, unsaved: bool
) -> str:
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
            name += f"({len(duplicates)})"

    if unsaved:
        name += "*"
    return name


class Document(Model):
    #: Name of the current document
    name = Str().tag(config=True)

    #: Source code
    source = Str()
    cursor = Tuple(default=(0, 0))

    #: Any unsaved changes
    unsaved = Bool(False)

    #: Version number
    version = Int(1)

    #: Any linting errors
    errors = List(CodeEditorIndicator)

    #: Any script output
    output = ContainerList(str)

    #: Any autocomplete suggestions
    suggestions = List()

    #: For testing
    plugin = ForwardTyped(lambda: EditorPlugin)

    #: Outline for outline view
    outline = List(Outline)

    #: Parsing task
    parsing = Bool()

    def exists(self) -> bool:
        return os.path.exists(self.name)

    def load(self):
        self.source = self._default_source()

    def __repr__(self):
        return f"Document<name='{self.name}'>"

    def append_output(self, output: str):
        """Limit output to 1000 entries"""
        if len(self.output) > 1000:
            self.output.pop(0)
        self.output.append(output)

    def _default_source(self) -> str:
        """Load the document from the path given by `name`.
        If it fails to load, nothing will be returned and an error
        will be set.
        """
        try:
            log.debug(f"Loading '{self.name}' from disk.")
            with open(self.name) as f:
                return f.read()
        except Exception as e:
            self.errors = [CodeEditorIndicator(title=str(e))]
        return ""

    def _observe_unsaved(self, change):
        """Increment the version number when unsaved is changed to false"""
        if change["type"] == "update" and not change["value"]:
            self.version += 1

    def _observe_source(self, change):
        deferred_call(self.reparse)
        if change["type"] == "update":
            try:
                if self.exists():
                    in_mem = source_hash(self.source, is_file=False)
                    on_disk = source_hash(self.name, is_file=True)
                    self.unsaved = in_mem != on_disk
            except Exception as e:
                log.debug(e)

    async def reparse(self):
        if self.parsing:
            log.debug(f"Reparse '{self.name}' skipped. alreading parsing")
            return
        self.parsing = True
        try:
            plugin = self.plugin
            if not plugin:
                log.debug(f"Reparse '{self.name}' skipped. No plugin")
                return
            langserver = plugin.langserver
            if not langserver or not plugin.langserver.connected:
                log.debug(f"Reparse '{self.name}' skipped. Langserver not connected")
                return
            log.debug(f"Reparse '{self.name}'")

            response: Optional[ParseResult] = await langserver.parse(
                self.name, self.source, self.version
            )
            if not response:
                return
            errors = []
            for p in response.problems:
                log.debug(f"Problem: {p.__getstate__()}")
                indicator = CodeEditorIndicator(
                    title=f"{p.type}: {p.msg}",
                    style=p.level,
                    start=(p.lineno, p.offset),
                    stop=(p.end_lineno, p.end_offset),
                )
                errors.append(indicator)

            self.errors = errors
            self.outline = response.outline
        except Exception as e:
            log.exception(e)
        finally:
            self.parsing = False


class LangServerRemoteProtocol(JsonRpcProtocol):
    #: Reference to the Editor plugin
    plugin = ForwardTyped(lambda: EditorPlugin)

    def connection_made(self, transport):
        self.transport = transport
        self.connected = True
        log.debug(f"Langserver connected {transport}")
        deferred_call(self.parse_active_document)

    def connection_lost(self, err):
        self.connected = False
        log.debug(f"Langserver connection lost {err}")

    def on_print(self, message: str):
        log.debug(f"langserver: {message}")

    async def parse_active_document(self):
        if doc := self.plugin.active_document:
            await doc.reparse()

    async def parse(
        self, filename: str, source: str, version: int
    ) -> Optional[ParseResult]:
        return await self.invoke_method("parse", filename, source, version)


class LangServerProcess(ProcessLineReceiver):
    #: Process handle
    plugin = ForwardTyped(lambda: EditorPlugin)
    process = Instance(object)

    #: Set to avoid restarting
    terminated = Bool()

    #: Count restarts so we can detect issues with startup
    restarts = Int()

    #: Max number it will attempt to restart
    max_retries = Int(3)

    async def start(self):
        cmd = get_bootstrap_cmd() + ["langserver", f"{self.plugin.port}"]
        log.debug(f"Starting langserver '{' '.join(cmd)}'")
        loop = asyncio.get_event_loop()
        self.process = await loop.subprocess_exec(lambda: self, *cmd)
        return self.process

    def data_received(self, data: bytes):
        """Called for stdout data and stderr data if err_to_out is True

        Parameters
        ----------
        data: Bytes
            The data received

        """
        log.debug(f"langserver | {data.decode().rstrip()}")

    def restart(self):
        self.restarts += 1
        if self.restarts > self.max_retries:
            log.debug("langserver | Restarts exceeded. Aborting")
            if workbench := self.plugin.workbench:
                workbench.message_critical(
                    "Langserver failed to start",
                    "Could not get the langserver to start after several attempts.",
                )
            return
        log.debug("langserver | Attempting to restart")
        deferred_call(self.start)

    def process_exited(self, reason=None):
        log.warning(f"langserver | process ended: {reason}")
        if not self.terminated:
            # Clear the filename on crash so it works when reset
            self.restart()
        log.warning("langserver | stdout closed")


class EditorPlugin(Plugin):
    #: Opened files
    documents = ContainerList(Document).tag(config=True)
    active_document = Instance(Document, ()).tag(config=True)
    last_path = Str(os.path.expanduser("~/")).tag(config=True)
    project_path = Str(os.path.expanduser("~/")).tag(config=True)

    #: Editor settings
    theme = Enum("default", *THEMES.keys()).tag(config=True)
    zoom = Int(0).tag(config=True)  #: Relative to default
    auto_parentheses = Bool(True).tag(config=True)
    tab_replace = Bool(True).tag(config=True)
    tab_width = Range(1, value=4).tag(config=True)
    auto_indent = Bool(True).tag(config=True)
    indent_size = Range(1, value=4).tag(config=True)
    show_line_numbers = Bool(True).tag(config=True)
    line_wrap = Bool(False).tag(config=True)

    code_folding = Bool(True).tag(config=True)
    code_fold_style = Enum(
        "plain", "circled", "boxed", "circled-tree", "boxed-tree"
    ).tag(config=True)
    font_size = Int(12).tag(config=True)  #: Default is 12 pt
    font_family = Str(MONO_FONT.split()[-1]).tag(config=True)
    show_scrollbars = Bool(True).tag(config=True)
    file_associations = Dict(
        default={
            "c": "c",
            "cpp": "cpp",
            "cxx": "cpp",
            "py": "python",
            "pyx": "python",
            "pyd": "python",
            "pyi": "python",
            "ino": "cpp",
            "sh": "bash",
            "yml": "yaml",
            "js": "javascript",
            "ts": "javascript",
            "jsx": "javascript",
            "md": "markdown",
            "gcode": "gcode",
            "nc": "gcode",
            "ncc": "gcode",
            "tap": "gcode",
            "svg": "xml",
        }
    ).tag(config=True)

    #: Key mappings
    key_mapping = Dict(
        default={
            "find": "\x06",  # Ctrl+F
            "replace": "\x12",  # Ctrl+R
            "goto": "\x0c",  # Ctrl + L
        }
    ).tag(config=True)

    #: Editor sys path
    sys_path = List().tag(config=True)
    _area_saves_pending = Int()

    # Langserver
    enable_langserver = Bool(True)
    langserver = Typed(LangServerRemoteProtocol)
    port = Int()
    langserver_server = Instance(asyncio.Server)
    langserver_process = Typed(LangServerProcess)

    def start(self, initial_document: Optional[Document] = None):
        """Make sure the documents all open on startup"""
        super().start()
        if initial_document:
            # If using the standalone editor avoid loading all
            # the workbench's documents which are restored automatically
            # in the super() call.
            self.documents = [initial_document]
            self.active_document = initial_document
        for doc in self.documents:
            doc.plugin = self
        if self.enable_langserver:
            deferred_call(self.start_langserver)
        if self.workbench is not None:
            deferred_call(self._update_area_layout, {"type": "load"})

    async def start_langserver(self):
        """Start both a server to listen for a langserver connection
        and the langserver process."""
        loop = asyncio.get_event_loop()
        self.langserver = LangServerRemoteProtocol(plugin=self)
        server = self.langserver_server = await loop.create_server(
            lambda: self.langserver, "127.0.0.1", 0
        )
        socket = server.sockets[0]
        ip, self.port = socket.getsockname()
        log.info(f"Listening for langserver on dcad://{ip}:{self.port}")
        langserver_process = self.langserver_process = LangServerProcess(
            err_to_out=True, plugin=self
        )
        deferred_call(langserver_process.start)

    # -------------------------------------------------------------------------
    # Editor API
    # -------------------------------------------------------------------------
    @observe("documents")
    def _update_area_layout(self, change):
        """When a document is opened or closed, add or remove it
        from the currently active TabLayout.

        The layout update is deferred so it fires after the items are
        updated by the Looper.

        """
        if change["type"] == "create":
            return

        if not self.workbench:
            return  # standalone editor

        #: Get the dock area
        area = self.get_dock_area()

        #: Refresh the dock items
        # area.looper.iterable = self.documents[:]

        #: Determine what change to apply
        removed = set()
        added = set()
        if change["type"] == "container":
            op = change["operation"]
            if op in ["append", "insert"]:
                added = set([change["item"]])
            elif op == "extend":
                added = set(change["items"])
            elif op in ["pop", "remove"]:
                removed = set([change["item"]])
        elif change["type"] == "update":
            old = set(change["oldvalue"])
            new = set(change["value"])

            #: Determine which changed
            removed = old.difference(new)
            added = new.difference(old)
        elif change["type"] == "load":
            removed = {item.doc for item in self.get_editor_items()}
            added = set(self.documents)

        #: Update operations to apply
        ops = []
        removed_targets = set()

        #: Remove any old items
        for doc in removed:
            for item in self.get_editor_items():
                if item.doc == doc:
                    removed_targets.add(item.name)
                    ops.append(RemoveItem(item=item.name))

        # Remove ops
        if ops:
            area.update_layout(ops)

        # Add each one at a time
        targets = set(
            [
                item.name
                for item in area.dock_items()
                if (
                    item.name.startswith("editor-item")
                    and item.name not in removed_targets
                )
            ]
        )

        # log.debug(
        #    "Editor added=%s removed=%s targets=%s", added, removed, targets)

        # Sort documents so active is last so it's on top when we restore
        # from a previous state
        for doc in sorted(added, key=lambda d: int(d == self.active_document)):
            item = create_editor_item(area, plugin=self, doc=doc)
            if targets:
                op = InsertTab(item=item.name, target=list(targets)[-1])
                try:
                    area.update_layout(op)
                except Exception as e:
                    # If it fails to add as a tab just insert it
                    log.exception(e)
                    op = InsertItem(item=item.name)
                    area.update_layout(op)
            else:
                op = InsertItem(item=item.name)
                area.update_layout(op)
            targets.add(item.name)

        # Now save it
        self.save_dock_area(change)

    def save_dock_area(self, change):
        """Save the dock area"""
        self._area_saves_pending += 1

        def do_save():
            self._area_saves_pending -= 1
            if self._area_saves_pending != 0:
                return
            #: Now save it
            ui = self.workbench.get_plugin("enaml.workbench.ui")
            ui.workspace.save_area()

        timed_call(350, do_save)

    def get_dock_area(self):
        """Alias to the `declaracad.ui` plugins `get_dock_area()`"""
        ui = self.workbench.get_plugin("declaracad.ui")
        return ui.get_dock_area()

    def get_editor(self, document: Optional[Document] = None):
        """Get the editor item for the currently active document"""
        doc = document or self.active_document
        for item in self.get_editor_items():
            if item.doc == doc:
                return item.editor

    def get_editor_items(self):
        dock = self.get_dock_area()
        EditorDockItem = editor_item_factory()
        for item in dock.dock_items():
            if isinstance(item, EditorDockItem):
                yield item

    # -------------------------------------------------------------------------
    # Document API
    # -------------------------------------------------------------------------
    def _default_documents(self) -> list[Document]:
        return [
            Document(
                name=os.path.expanduser("~/Documents/example.enaml"),
                unsaved=True,
                source=EXAMPLE_FILE,
                plugin=self,
            )
        ]

    def _default_active_document(self) -> Document:
        if not self.documents:
            self.documents = self._default_documents()
        return self.documents[0]

    def new_file(self, event: Union[str, ExecutionEvent]):
        """Create a new file with the given path"""
        if isinstance(event, ExecutionEvent):
            path = event.parameters.get("path")
        else:
            path = event

        if not path:
            return
        if not os.path.dirname(path):
            path = os.path.join(self.project_path, path)
        doc = Document(name=path, plugin=self, source=NEW_FILE_SOURCE)
        self.documents.append(doc)
        self.active_document = doc

    def close_file(self, event: Union[str, ExecutionEvent]):
        """Close the file with the given path and remove it from
        the document list. If multiple documents with the same file
        are open this only closes the first one it finds.

        """
        if isinstance(event, ExecutionEvent):
            path = event.parameters.get("path")
        else:
            path = event

        # Default to current document
        if path is None:
            path = self.active_document.name
        docs = self.documents
        opened = [d for d in docs if d.name == path]
        if not opened:
            return
        log.debug("Closing '%s'", path)
        doc = opened[0]
        self.documents.remove(doc)

        # If any viewer was bound to this document, unbind it
        viewer_plugin = self.workbench.get_plugin("declaracad.viewer")
        for viewer in viewer_plugin.get_viewers():
            if viewer.document == doc:
                viewer.document = None

        # If we removed all of them create a new empty one
        if not self.documents:
            self.documents = self._default_documents()
            self.active_document = self.documents[0]

        # If we closed the active document
        elif self.active_document == doc:
            self.active_document = self.documents[0]

    def open_file(self, event: Union[str, ExecutionEvent]):
        """Open a file from the local filesystem"""
        if isinstance(event, ExecutionEvent):
            path = event.parameters["path"]
        else:
            path = event

        #: Check if the document is already open
        for doc in self.documents:
            if doc.name == path:
                self.active_document = doc
                return
        log.debug("Opening '%s'", path)

        #: Otherwise open it
        doc = Document(name=path, unsaved=False, plugin=self)
        doc.load()
        self.documents.append(doc)
        self.active_document = doc
        if editor := self.get_editor():
            editor.set_text(doc.source)

    def open_containing_folder(self, event: Union[str, ExecutionEvent]):
        """Open the folder containing the given file path"""
        if isinstance(event, ExecutionEvent):
            path = event.parameters["path"]
        else:
            path = event
        folder = os.path.dirname(path)
        if not os.path.exists(folder):
            return
        if "win32" in sys.platform:
            os.startfile(folder, "explore")  # type: ignore
        elif sys.platform == "darwin":
            subprocess.call(["open", folder])
        else:
            subprocess.call(["xdg-open", folder])

    def save_file(self, event: ExecutionEvent):
        """Save the currently active document to disk"""
        # Make sure it's in sync with the editor first
        editor = self.get_editor()
        doc = self.active_document
        doc.source = editor.get_text()
        assert doc.name, "Can't save a document without a name"
        file_dir = os.path.dirname(doc.name)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir)
        with open(doc.name, "w") as f:
            f.write(doc.source)
        doc.unsaved = False

    def save_file_as(self, event: Union[str, ExecutionEvent]):
        """Save the currently active document as the given name
        overwriting and creating the directory path if necessary.

        """
        doc = self.active_document
        if isinstance(event, ExecutionEvent):
            path = event.parameters["path"]
        else:
            path = event

        if not doc.name:
            doc.name = path
            doc.unsaved = False

        doc_dir = os.path.dirname(path)
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir)

        with open(path, "w") as f:
            f.write(doc.source)

    def reload_document(self, document: Document):
        """Reload the source from disk

        Parameters
        ----------
        document: Document
            The document to reload

        """
        document.load()
        # Update the editor
        for item in self.get_editor_items():
            if item.doc == document:
                item.editor.set_text(document.source)

    # -------------------------------------------------------------------------
    # Code inspection API
    # -------------------------------------------------------------------------
    def detect_syntax(self, path: str) -> str:
        """Attempt to detect the file syntax"""
        p, ext = os.path.splitext(path)
        file_type = (ext[1:] if ext else "").lower()
        if file_type in SYNTAXES:
            result = file_type
        else:
            result = self.file_associations.get(file_type, "")
        log.info(f"Using syntax: {result}")
        return result

    def _default_sys_path(self) -> list[str]:
        """Determine the sys path"""
        return [self.project_path]

    @observe("project_path")
    def _refresh_sys_path(self, change):
        if change["type"] == "update":
            self.sys_path = self._default_sys_path()
