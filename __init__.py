"""
Chord Song Blender Add-on.

Vim-like <Leader> chord launcher with which-key style overlay.
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,wrong-import-position,broad-exception-caught,import-outside-toplevel
# ruff: noqa: E402

import bpy

from .utils.addon_package import addon_root_package
from .ui import (
    CHORDSONG_Preferences,
    CHORDSONG_PG_Group,
    CHORDSONG_PG_Mapping,
    CHORDSONG_PG_NerdIcon,
    CHORDSONG_PG_SubItem,
    CHORDSONG_PG_SubOperator,
    CHORDSONG_PG_ScriptParam,
)
from .operators import (
    CHORDSONG_OT_Append_Config,
    CHORDSONG_OT_ApplyConflictFix,
    CHORDSONG_OT_CheckConflicts,
    CHORDSONG_OT_MergeIdentical,
    CHORDSONG_OT_ContextMenu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Fold_All,
    CHORDSONG_OT_Group_Move_Up,
    CHORDSONG_OT_Group_Move_Down,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Group_Unfold_All,
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
    CHORDSONG_OT_Property_Mapping_Convert,
    CHORDSONG_OT_Open_Keymap,
    CHORDSONG_OT_Open_Prefs,
    CHORDSONG_OT_Recents,
    CHORDSONG_OT_Save_Config,
    CHORDSONG_OT_Script_Select,
    CHORDSONG_OT_Script_Select_Apply,
    CHORDSONG_OT_SubItem_Add,
    CHORDSONG_OT_SubItem_Remove,
    CHORDSONG_OT_TestFadingOverlay,
    CHORDSONG_OT_TestMainOverlay,
    CHORDSONG_PG_GroupSelection,
    cleanup_all_handlers,
    register_context_menu,
    unregister_context_menu,
)

_classes = (
    CHORDSONG_PG_NerdIcon,
    CHORDSONG_PG_SubItem,
    CHORDSONG_PG_SubOperator,
    CHORDSONG_PG_ScriptParam,
    CHORDSONG_PG_Group,
    CHORDSONG_PG_Mapping,
    CHORDSONG_PG_GroupSelection,
    CHORDSONG_Preferences,
    CHORDSONG_OT_Append_Config,
    CHORDSONG_OT_ApplyConflictFix,
    CHORDSONG_OT_CheckConflicts,
    CHORDSONG_OT_ContextMenu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Fold_All,
    CHORDSONG_OT_Group_Move_Up,
    CHORDSONG_OT_Group_Move_Down,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Group_Unfold_All,
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
    CHORDSONG_OT_MergeIdentical,
    CHORDSONG_OT_Property_Mapping_Convert,
    CHORDSONG_OT_Open_Keymap,
    CHORDSONG_OT_Open_Prefs,
    CHORDSONG_OT_Recents,
    CHORDSONG_OT_Save_Config,
    CHORDSONG_OT_Script_Select,
    CHORDSONG_OT_Script_Select_Apply,
    CHORDSONG_OT_SubItem_Add,
    CHORDSONG_OT_SubItem_Remove,
    CHORDSONG_OT_TestFadingOverlay,
    CHORDSONG_OT_TestMainOverlay,
)

addon_keymaps = []

def _safe_register_class(cls):
    """Register a class, recovering from partial/failed previous registrations."""
    try:
        bpy.utils.register_class(cls)
    except ValueError:
        # Most commonly: "already registered as a subclass ..."
        try:
            bpy.utils.unregister_class(cls)
        except Exception:
            pass
        bpy.utils.register_class(cls)

def _safe_unregister_class(cls):
    try:
        bpy.utils.unregister_class(cls)
    except Exception:
        pass

def register():
    """Register addon classes and keymaps."""
    for cls in _classes:
        _safe_register_class(cls)

    # handle the keymap
    wm = bpy.context.window_manager

    # 3D View
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, 'SPACE', 'PRESS')
    addon_keymaps.append((km, kmi))

    # Node Editor
    km = wm.keyconfigs.addon.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')
    kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, 'SPACE', 'PRESS')
    addon_keymaps.append((km, kmi))

    # Image Editor
    km = wm.keyconfigs.addon.keymaps.new(name='Image Editor', space_type='IMAGE_EDITOR')
    kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, 'SPACE', 'PRESS')
    addon_keymaps.append((km, kmi))

    register_context_menu()
    # Initialize default config path early (so operators can use it before opening prefs UI).
    try:
        package_name = addon_root_package(__package__)
        prefs = bpy.context.preferences.addons[package_name].preferences
        if hasattr(prefs, "ensure_defaults"):
            prefs.ensure_defaults()

        # Load default config on first install (when no user config exists)
        import os
        from .core.config_io import apply_config, loads_json
        from .ui.prefs import default_config_path

        # Check if user has any mappings (indicates they've already configured)
        has_existing_config = len(getattr(prefs, "mappings", [])) > 0

        # Also check if a config file exists at the default path
        default_path = default_config_path()
        config_file_exists = default_path and os.path.exists(default_path)

        # Only load default config if this appears to be a first install
        if not has_existing_config and not config_file_exists:
            # Load default config from bundled file
            try:
                # Get path to bundled default_mappings.json
                from .operators.config.load_default import _get_default_config_path
                bundled_config_path = _get_default_config_path()

                if os.path.exists(bundled_config_path):
                    with open(bundled_config_path, "r", encoding="utf-8") as f:
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
    # Clean up any active draw handlers/timers first to avoid draw-state conflicts
    try:
        cleanup_all_handlers()
    except Exception:
        pass

    unregister_context_menu()

    # Clear keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    for cls in reversed(_classes):
        _safe_unregister_class(cls)
