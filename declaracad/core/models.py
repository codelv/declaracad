"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 6, 2017

@author: jrm
"""

import json
import os
import traceback

import enaml
import jsonpickle as pickle
from atom.api import Atom, Dict, List, Member, Set, Str
from enaml.widgets.api import Container
from enaml.workbench.plugin import Plugin as EnamlPlugin

from .utils import clip, log


# -----------------------------------------------------------------------------
# Core models
# -----------------------------------------------------------------------------
class Model(Atom):
    """An atom object that can exclude members from it's state
    by tagging the member with .tag(persist=False)

    """

    def __getstate__(self):
        """Exclude any members from the state that are not tagged with
        `config=True`.

        """
        state = super(Model, self).__getstate__()
        for name, member in self.members().items():
            metadata = member.metadata
            if name in state and (not metadata or not metadata.get("config", False)):
                del state[name]
        return state

    def __setstate__(self, state):
        """Set the state ignoring any fields that fail to set which
        may occur due to version changes.

        """
        for key, value in state.items():
            # log.debug("Restoring state '{}.{} = {}'".format(
            #    self, key, clip(value)
            # ))
            try:
                setattr(self, key, value)
            except Exception as e:
                #: Shorten any long values
                log.warning(
                    "Failed to restore state '{}.{} = {}' (reason: {})".format(
                        self, key, clip(value), e
                    )
                )


class Plugin(EnamlPlugin):
    """A plugin that behaves like a model and saves it's state
    when any atom member tagged with config=True triggers a save.

    Also optionally registers itself in the settings

    """

    #: Settings pages this plugin adds
    settings_pages = Dict(Atom, Container)
    settings_items = List(Atom)

    #: File used to save and restore the state for this plugin
    _state_file = Str()
    _state_members = List(Member)

    #: Set of fields which are frozen. These will not be modified by
    #: saving and restoring.
    frozen_fields = Set()
    _frozen_state = Dict()

    # -------------------------------------------------------------------------
    # Plugin API
    # -------------------------------------------------------------------------
    def start(self):
        """Load the state when the plugin starts"""
        log.debug("Starting plugin '{}'".format(self.manifest.id))
        self._bind_observers()

    def stop(self):
        """Unload any state observers when the plugin stops"""
        self._unbind_observers()

    # -------------------------------------------------------------------------
    # State API
    # -------------------------------------------------------------------------
    def save(self):
        """Manually trigger a save"""
        self._save_state({"type": "request"})

    def restore(self):
        """Force restore from config"""
        self._unbind_observers()
        self._bind_observers()

    def _default__state_file(self):
        return os.path.expanduser(
            "~/.config/declaracad/{}.json".format(self.manifest.id)
        )

    def _default__state_members(self):
        members = []  #: Init state members
        for name, member in self.members().items():
            if member.metadata and member.metadata.get("config", False):
                members.append(member)
        return members

    def _bind_observers(self):
        """Try to load the plugin state"""
        try:
            if os.path.exists(self._state_file):
                with enaml.imports():
                    with open(self._state_file, "r") as f:
                        state = pickle.loads(f.read())

                frozen_state = {}
                for k in self.frozen_fields:
                    if k in state:
                        frozen_state[k] = state.pop(k)

                self.__setstate__(state)
                self._frozen_state = frozen_state
                # log.debug("Plugin {} state restored from: {}".format(
                #    self.manifest.id, self._state_file))
        except Exception:
            log.warning(
                "Plugin {} failed to load state: {}".format(
                    self.manifest.id, traceback.format_exc()
                )
            )

        #: Hook up observers
        for member in self._state_members:
            self.observe(member.name, self._save_state)

    def _save_state(self, change):
        """Try to save the plugin state"""
        if change["type"] not in ("update", "container", "request"):
            return

        try:
            log.info("Saving: {} due to {}".format(self._state_file, change))

            #: Dump first so any failure to encode doesn't wipe out the
            #: previous state
            state = self.__getstate__()
            excluded = ["manifest", "workbench"] + [
                m.name
                for m in self.members().values()
                if not m.metadata or not m.metadata.get("config", False)
            ]
            for k in excluded:
                if k in state:
                    del state[k]

            # Replace any frozen members
            state.update(self._frozen_state)

            state = pickle.dumps(state)

            #: Pretty format it
            state = json.dumps(json.loads(state), indent=2)

            dst = os.path.dirname(self._state_file)
            if not os.path.exists(dst):
                os.makedirs(dst)

            with open(self._state_file, "w") as f:
                f.write(state)

        except Exception:
            log.warning("Failed to save state: {}".format(traceback.format_exc()))

    def _unbind_observers(self):
        """Setup state observers"""
        for member in self._state_members:
            self.unobserve(member.name, self._save_state)

    # -------------------------------------------------------------------------
    # Settings API
    # -------------------------------------------------------------------------
    def _default_settings_pages(self):
        """Available settings pages"""
        return {}

    def _default_settings_items(self):
        return []
