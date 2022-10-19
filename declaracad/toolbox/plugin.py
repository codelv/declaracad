# -*- coding: utf-8 -*-
"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Dec 10, 2015

@author: jrm
"""
import inspect
import logging

from atom.api import Atom, List, Str, Subclass, Value
from enaml.application import Application

from declaracad.core.api import Model, Plugin, log


def get_all_modules():
    from declaracad.cnc import api as cnc_api
    from declaracad.fea import api as fea_api
    from declaracad.occ import api as occ_api

    return (occ_api, cnc_api, fea_api)


class UnknownProxy(Atom):
    pass


class Tool(Model):
    name = Str()
    declaration = Subclass(Atom)
    proxy = Subclass(Atom)
    module = Value()
    doc = Str()

    def _default_doc(self) -> str:
        return inspect.getdoc(self.declaration) or ""

    def _default_proxy(self):
        # app = Application.instance()
        # factory = app.resolver.factories.get(self.name)
        # if factory:
        #     return factory()
        return UnknownProxy


class ToolboxPlugin(Plugin):

    #: List of tools or
    tools = List(Tool)

    def _refresh_tools(self) -> None:
        tools: list[Tool] = []
        excluded = ("load_model",)
        for module in get_all_modules():
            for name in dir(module):
                if name.startswith("_") or name in excluded:
                    continue
                d = getattr(module, name)
                try:
                    if not issubclass(d, Atom):
                        continue
                except TypeError:
                    continue  # Not a class
                tool = Tool(name=name, module=module, declaration=d)
                tools.append(tool)
        tools.sort(key=lambda it: it.name)
        log.debug("Tools loaded")
        self.tools = tools

    def start(self) -> None:
        log = logging.getLogger("MARKDOWN")
        log.setLevel(logging.WARNING)
        app = Application.instance()
        # Defer this to speed up startup time
        # TODO: Connect this to some sort of event
        app.timed_call(3000, self._refresh_tools)
