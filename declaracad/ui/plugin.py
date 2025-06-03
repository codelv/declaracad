"""
Copyright (c) 2017, Jairus Martin.

Distributed under the terms of the GPL v3 License.

The full license is in the file LICENSE, distributed with this software.

Created on Jul 12, 2015

@author: jrm
"""

import enaml
from atom.api import Atom, Enum, Instance, List, Str
from enaml.layout.api import (
    AreaLayout,
    DockBarLayout,
    HSplitLayout,
    TabLayout,
    VSplitLayout,
)

from declaracad.core.api import DockItem, Plugin, log

from . import extensions

with enaml.imports():
    from enaml.stdlib.dock_area_styles import available_styles


ALL_STYLES = ["system"] + available_styles()


class DeclaracadPlugin(Plugin):
    #: Project site
    wiki_page = Str("https;//declaracad.com/")

    #: Dock items to add
    dock_items = List(DockItem)
    dock_layout = Instance(AreaLayout)
    dock_style = Enum(*reversed(ALL_STYLES)).tag(config=True)

    #: Settings pages to add
    settings_pages = List(extensions.SettingsPage)

    #: Current settings page
    settings_page = Instance(extensions.SettingsPage)

    #: Internal settings models
    settings_model = Instance(Atom)

    def start(self):
        """Load all the plugins declaracad is dependent on"""
        super(DeclaracadPlugin, self).start()
        self._refresh_dock_items()
        self._refresh_settings_pages()

    def _bind_observers(self):
        """Setup the observers for the plugin."""
        super(DeclaracadPlugin, self)._bind_observers()
        workbench = self.workbench
        point = workbench.get_extension_point(extensions.DOCK_ITEM_POINT)
        point.observe("extensions", self._refresh_dock_items)

        point = workbench.get_extension_point(extensions.SETTINGS_PAGE_POINT)
        point.observe("extensions", self._refresh_settings_pages)

    def _unbind_observers(self):
        """Remove the observers for the plugin."""
        super(DeclaracadPlugin, self)._unbind_observers()
        workbench = self.workbench
        point = workbench.get_extension_point(extensions.DOCK_ITEM_POINT)
        point.unobserve("extensions", self._refresh_dock_items)

        point = workbench.get_extension_point(extensions.SETTINGS_PAGE_POINT)
        point.unobserve("extensions", self._refresh_settings_pages)

    # -------------------------------------------------------------------------
    # Dock API
    # -------------------------------------------------------------------------
    def create_new_area(self):
        """Create the dock area"""
        with enaml.imports():
            from .dock import DockView
        area = DockView(workbench=self.workbench, plugin=self)
        return area

    def get_dock_area(self):
        """Get the dock area

        Returns
        -------
            area: DockArea
        """
        ui = self.workbench.get_plugin("enaml.workbench.ui")
        if not ui.workspace or not ui.workspace.content:
            ui.select_workspace("declaracad.workspace")
        return ui.workspace.content.find("dock_area")

    def _refresh_dock_items(self, change=None):
        """Reload all DockItems registered by any Plugins

        Any plugin can add to this list by providing a DockItem
        extension in their PluginManifest.

        """
        workbench = self.workbench
        point = workbench.get_extension_point(extensions.DOCK_ITEM_POINT)

        #: Layout spec
        layout = {name: [] for name in extensions.DockItem.layout.items}

        dock_items = []
        for extension in sorted(point.extensions, key=lambda ext: ext.rank):
            for declaration in extension.get_children(extensions.DockItem):
                # Create the item
                DockItem = declaration.factory()
                plugin = workbench.get_plugin(declaration.plugin_id)
                item = DockItem(plugin=plugin)

                # Add to our layout
                layout[declaration.layout].append(item.name)

                # Save it
                dock_items.append(item)

        # Update items
        # log.debug("Updating dock items: {}".format(dock_items))
        self.dock_items = dock_items
        self._refresh_layout(layout)

    def _refresh_layout(self, layout):
        """Create the layout for all the plugins"""
        if not self.dock_items:
            return AreaLayout()
        items = layout.pop("main")
        if not items:
            raise EnvironmentError("At least one main layout item must be " "defined!")

        left_items = layout.pop("main-left", [])
        bottom_items = layout.pop("main-bottom", [])

        main = TabLayout(*items)

        if bottom_items:
            main = VSplitLayout(main, *bottom_items)
        if left_items:
            main = HSplitLayout(*left_items, main)

        dockbars = [
            DockBarLayout(*items, position=side)
            for side, items in layout.items()
            if items
        ]

        #: Update layout
        self.dock_layout = AreaLayout(main, dock_bars=dockbars)

    # -------------------------------------------------------------------------
    # Settings API
    # -------------------------------------------------------------------------
    def _default_settings_page(self):
        return self.settings_pages[0]

    def _observe_settings_page(self, change):
        log.debug("Settings page: {}".format(change))

    def _refresh_settings_pages(self, change=None):
        """Reload all SettingsPages registered by any Plugins

        Any plugin can add to this list by providing a SettingsPage
        extension in their PluginManifest.

        """
        workbench = self.workbench
        point = workbench.get_extension_point(extensions.SETTINGS_PAGE_POINT)

        settings_pages = []
        for extension in sorted(point.extensions, key=lambda ext: ext.rank):
            for d in extension.get_children(extensions.SettingsPage):
                settings_pages.append(d)

        #: Update items
        settings_pages.sort(key=lambda p: p.name)
        # log.debug("Updating settings pages: {}".format(settings_pages))
        self.settings_pages = settings_pages
