"""
Chord Song Blender Add-on.

Vim-like <Leader> chord launcher with which-key style overlay.
"""

bl_info = {
    "name": "Chord Song",
    "author": "Cyrill Vitkovskiy",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "Preferences > Add-ons > Chord Song",
    "description": "Vim-like <Leader> chord launcher with which-key style overlay",
    "category": "Interface",
}

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,wrong-import-position,broad-exception-caught,import-outside-toplevel
# ruff: noqa: E402

import bpy

from .ui import CHORDSONG_Preferences, CHORDSONG_PG_Group, CHORDSONG_PG_Mapping, CHORDSONG_PG_NerdIcon
from .operators import (
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Icon_Select,
    CHORDSONG_OT_Icon_Select_Apply,
    CHORDSONG_OT_Leader,
    CHORDSONG_OT_Load_Autosave,
    CHORDSONG_OT_Load_Config,
    CHORDSONG_OT_Load_Default,
    CHORDSONG_OT_Mapping_Add,
    CHORDSONG_OT_Mapping_Convert,
    CHORDSONG_OT_Mapping_Duplicate,
    CHORDSONG_OT_Mapping_Remove,
    CHORDSONG_OT_Open_Keymap,
    CHORDSONG_OT_Open_Prefs,
    CHORDSONG_OT_Save_Config,
)

_classes = (
    CHORDSONG_PG_NerdIcon,
    CHORDSONG_PG_Group,
    CHORDSONG_PG_Mapping,
    CHORDSONG_Preferences,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Icon_Select,
    CHORDSONG_OT_Icon_Select_Apply,
    CHORDSONG_OT_Leader,
    CHORDSONG_OT_Load_Autosave,
    CHORDSONG_OT_Load_Config,
    CHORDSONG_OT_Load_Default,
    CHORDSONG_OT_Mapping_Add,
    CHORDSONG_OT_Mapping_Convert,
    CHORDSONG_OT_Mapping_Duplicate,
    CHORDSONG_OT_Mapping_Remove,
    CHORDSONG_OT_Open_Keymap,
    CHORDSONG_OT_Open_Prefs,
    CHORDSONG_OT_Save_Config,
)

_addon_keymaps = []


def rebuild_keymaps():
    """Recreate add-on keymaps."""
    _unregister_keymaps()
    _register_keymaps()


def _register_keymaps():
    # Bind leader key in 3D View to start chord capture.
    # Users can also change this in Blender Keymap settings under Add-ons.
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    leader_key = "SPACE"

    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
    kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, type=leader_key, value="PRESS")
    _addon_keymaps.append((km, kmi))


def _unregister_keymaps():
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps.clear()


def register():
    """Register addon classes and keymaps."""
    for cls in _classes:
        bpy.utils.register_class(cls)
    _register_keymaps()
    # Initialize default config path early (so operators can use it before opening prefs UI).
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        if hasattr(prefs, "ensure_defaults"):
            prefs.ensure_defaults()

        # Try to load config from scripts/presets/chordsong/chordsong.json if it exists
        try:
            import os
            from .core.config_io import apply_config, loads_json
            from .ui.prefs import default_config_path

            config_path = default_config_path()
            if config_path and os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = loads_json(f.read())
                # Suspend autosave during initial load
                prefs._chordsong_suspend_autosave = True  # pylint: disable=protected-access
                try:
                    apply_config(prefs, data)
                finally:
                    prefs._chordsong_suspend_autosave = False  # pylint: disable=protected-access
        except Exception:
            # Silently ignore errors during initial config load
            # User can still load config manually if needed
            pass
    except Exception:
        pass


def unregister():
    """Unregister addon classes and keymaps."""
    _unregister_keymaps()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
