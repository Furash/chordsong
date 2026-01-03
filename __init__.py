"""
Chord Song Blender Add-on.

Vim-like <Leader> chord launcher with which-key style overlay.
"""

# bl_info is kept for backward compatibility and to avoid performance warnings.
# Extension metadata is primarily defined in blender_manifest.toml (Blender 4.2+).
# However, bl_info is still required for reload functionality to work properly.
bl_info = {
    "name": "Chord Song",
    "author": "Cyrill Vitkovskiy",
    "website": "https://github.com/Furash/chordsong/",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "Preferences > Add-ons > Chord Song",
    "description": "Vim-like <Leader> key implementation for Blender",
    "category": "Interface",
}

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,wrong-import-position,broad-exception-caught,import-outside-toplevel
# ruff: noqa: E402

import bpy

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
    CHORDSONG_OT_Context_Menu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Fold_All,
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
    CHORDSONG_OT_Context_Menu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Fold_All,
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

_addon_keymaps = []

def rebuild_keymaps():
    """Recreate add-on keymaps."""
    _unregister_keymaps()
    _register_keymaps()

def _register_keymaps():
    # Bind leader key in multiple editors to start chord capture.
    # Users can change this in Blender's Keymap editor under Add-ons > Chord Song.
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if not kc:
        return

    leader_key = "SPACE"

    def _add_keymap_item(keymap_name, space_type):
        """Helper to add keymap item, handling existing keymaps."""
        try:
            # Try to get existing keymap first
            km = kc.keymaps.get(keymap_name)
            if not km:
                # Create new keymap if it doesn't exist
                km = kc.keymaps.new(name=keymap_name, space_type=space_type)

            # Check if keymap item already exists
            existing_kmi = None
            for item in km.keymap_items:
                if item.idname == CHORDSONG_OT_Leader.bl_idname:
                    existing_kmi = item
                    break

            if existing_kmi:
                # Update existing keymap item
                existing_kmi.type = leader_key
                existing_kmi.value = "PRESS"
                _addon_keymaps.append((km, existing_kmi))
            else:
                # Create new keymap item
                kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, type=leader_key, value="PRESS")
                _addon_keymaps.append((km, kmi))
        except Exception as e:
            # Log error but continue with other keymaps
            print(f"Chord Song: Failed to register keymap for {keymap_name}: {e}")

    # Register for 3D View
    _add_keymap_item("3D View", "VIEW_3D")

    # Register for Node Editor (covers both Geometry Nodes and Shader Editor)
    _add_keymap_item("Node Editor", "NODE_EDITOR")

    # Register for UV/Image Editor
    # Try to find existing keymap with IMAGE_EDITOR space type, or create one.
    image_editor_km = None
    for km_name in kc.keymaps.keys():
        km_test = kc.keymaps.get(km_name)
        if km_test and hasattr(km_test, 'space_type') and km_test.space_type == 'IMAGE_EDITOR':
            image_editor_km = km_test
            break

    if image_editor_km:
        # Found existing Image Editor keymap, add our item to it
        existing_kmi = None
        for item in image_editor_km.keymap_items:
            if item.idname == CHORDSONG_OT_Leader.bl_idname:
                existing_kmi = item
                break

        if existing_kmi:
            existing_kmi.type = leader_key
            existing_kmi.value = "PRESS"
            _addon_keymaps.append((image_editor_km, existing_kmi))
        else:
            kmi = image_editor_km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, type=leader_key, value="PRESS")
            _addon_keymaps.append((image_editor_km, kmi))
    else:
        # No existing keymap found, try to create one
        # Try different possible names
        for name in ["Image Editor", "UV/Image Editor"]:
            try:
                km = kc.keymaps.new(name=name, space_type="IMAGE_EDITOR")
                kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, type=leader_key, value="PRESS")
                _addon_keymaps.append((km, kmi))
                break
            except Exception:
                continue

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
    register_context_menu()
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
    # Clean up any active draw handlers/timers first to avoid draw-state conflicts
    try:
        cleanup_all_handlers()
    except Exception:
        pass
    unregister_context_menu()
    _unregister_keymaps()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
