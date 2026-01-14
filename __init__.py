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
    CHORDSONG_OT_Clear_Search,
    CHORDSONG_OT_Clear_Operator_Cache,
    CHORDSONG_OT_CheckConflicts,
    CHORDSONG_OT_MergeIdentical,
    CHORDSONG_OT_ContextMenu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_ExportOverlayTheme,
    CHORDSONG_OT_ExtractBlenderTheme,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Edit,
    CHORDSONG_OT_Group_Fold_All,
    CHORDSONG_OT_Group_Move_Up,
    CHORDSONG_OT_Group_Move_Down,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Group_Unfold_All,
    CHORDSONG_OT_Icon_Select,
    CHORDSONG_OT_Icon_Select_Apply,
    CHORDSONG_OT_ImportOverlayTheme,
    CHORDSONG_OT_Leader,
    CHORDSONG_OT_Load_Autosave,
    CHORDSONG_OT_Load_Config,
    CHORDSONG_OT_Load_Default,
    CHORDSONG_OT_LoadThemePreset,
    CHORDSONG_OT_Mapping_Add,
    CHORDSONG_OT_Mapping_Convert,
    CHORDSONG_OT_Mapping_Duplicate,
    CHORDSONG_OT_Mapping_Fold_All,
    CHORDSONG_OT_Mapping_Remove,
    CHORDSONG_OT_Mapping_Unfold_All,
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
    CHORDSONG_OT_Clear_Search,
    CHORDSONG_OT_Clear_Operator_Cache,
    CHORDSONG_OT_CheckConflicts,
    CHORDSONG_OT_ContextMenu,
    CHORDSONG_OT_Export_Config,
    CHORDSONG_OT_Export_Config_Toggle_Groups,
    CHORDSONG_OT_ExportOverlayTheme,
    CHORDSONG_OT_ExtractBlenderTheme,
    CHORDSONG_OT_Group_Add,
    CHORDSONG_OT_Group_Cleanup,
    CHORDSONG_OT_Group_Edit,
    CHORDSONG_OT_Group_Fold_All,
    CHORDSONG_OT_Group_Move_Up,
    CHORDSONG_OT_Group_Move_Down,
    CHORDSONG_OT_Group_Remove,
    CHORDSONG_OT_Group_Rename,
    CHORDSONG_OT_Group_Select,
    CHORDSONG_OT_Group_Unfold_All,
    CHORDSONG_OT_Icon_Select,
    CHORDSONG_OT_Icon_Select_Apply,
    CHORDSONG_OT_ImportOverlayTheme,
    CHORDSONG_OT_Leader,
    CHORDSONG_OT_Load_Autosave,
    CHORDSONG_OT_Load_Config,
    CHORDSONG_OT_Load_Default,
    CHORDSONG_OT_LoadThemePreset,
    CHORDSONG_OT_Mapping_Add,
    CHORDSONG_OT_Mapping_Convert,
    CHORDSONG_OT_Mapping_Duplicate,
    CHORDSONG_OT_Mapping_Fold_All,
    CHORDSONG_OT_Mapping_Remove,
    CHORDSONG_OT_Mapping_Unfold_All,
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
    
    # Clear operator cache on addon enable to ensure fresh operator list
    try:
        from .ui.prefs import _clear_operator_cache
        _clear_operator_cache()
    except Exception:
        pass

    # === Keymap Registration ===
    # Register default SPACE key binding for leader operator
    wm = bpy.context.window_manager
    kc_addon = wm.keyconfigs.addon

    if kc_addon:
        addon_keymaps.clear()

        keymap_configs = [
            ('3D View', 'VIEW_3D'),
            ('Node Editor', 'NODE_EDITOR'),
            ('Image', 'IMAGE_EDITOR'),
        ]

        for km_name, space_type in keymap_configs:
            km = kc_addon.keymaps.new(name=km_name, space_type=space_type)

            # Check if keymap item already exists (avoid duplicates on reload)
            kmi = None
            for item in km.keymap_items:
                if item.idname == CHORDSONG_OT_Leader.bl_idname:
                    kmi = item
                    break

            if not kmi:
                # Create default SPACE key binding
                # User customizations in keyconfigs.user take precedence automatically
                kmi = km.keymap_items.new(CHORDSONG_OT_Leader.bl_idname, 'SPACE', 'PRESS')

            addon_keymaps.append((km, kmi))

    register_context_menu()

    # Restore user's config and auto-load their mappings on addon enable
    try:
        package_name = addon_root_package(__package__)
        prefs = bpy.context.preferences.addons[package_name].preferences

        # Suspend all property update callbacks during initialization to prevent spam
        # Must use module-level global because Blender reinitializes prefs during registration
        from .ui import prefs as prefs_module
        prefs_module._SUSPEND_CALLBACKS = True
        prefs._chordsong_suspend_autosave = True

        import os
        from .core.config_io import apply_config, loads_json
        from .ui.prefs import default_config_path

        # Restore user's config path from persistent storage
        # (config_path property doesn't persist across addon disable/enable)
        user_config_path = getattr(prefs, "config_path", "") or ""
        has_existing_mappings = len(getattr(prefs, "mappings", [])) > 0

        try:
            extension_dir = bpy.utils.extension_path_user(package_name, path="", create=True)
            if extension_dir:
                config_path_file = os.path.join(extension_dir, "config_path.txt")
                if os.path.exists(config_path_file):
                    with open(config_path_file, "r", encoding="utf-8") as f:
                        saved_path = f.read().strip()
                        if saved_path and os.path.exists(saved_path):
                            user_config_path = saved_path
        except Exception:
            pass

        user_config_exists = user_config_path and os.path.exists(user_config_path)

        try:
            # Restore the user's config path
            if user_config_path:
                prefs.config_path = user_config_path

            # Initialize defaults only on first install (no config path, no mappings)
            if not user_config_path and not has_existing_mappings:
                if hasattr(prefs, "ensure_defaults"):
                    prefs.ensure_defaults()

            # Auto-load user's config on addon enable
            # (mappings collection is cleared on disable, but config_path.txt persists)
            if not has_existing_mappings and user_config_exists:
                try:
                    with open(user_config_path, "r", encoding="utf-8") as f:
                        data = loads_json(f.read())
                    apply_config(prefs, data)
                except Exception:
                    pass

            # Load bundled default config only on first install (no saved config found)
            default_path = default_config_path()
            config_file_exists = default_path and os.path.exists(default_path)

            if not has_existing_mappings and not user_config_exists and not config_file_exists:
                try:
                    from .operators.config.load_default import _get_default_config_path
                    bundled_config_path = _get_default_config_path()

                    if os.path.exists(bundled_config_path):
                        with open(bundled_config_path, "r", encoding="utf-8") as f:
                            data = loads_json(f.read())
                        apply_config(prefs, data)
                except Exception:
                    pass
        finally:
            # Re-enable callbacks now that initialization is complete
            prefs_module._SUSPEND_CALLBACKS = False
            prefs._chordsong_suspend_autosave = False
    except Exception:
        pass

def unregister():
    """Unregister addon classes and keymaps."""
    # Clean up active draw handlers to prevent callbacks accessing invalid prefs
    try:
        cleanup_all_handlers()
    except Exception:
        pass

    # Cancel pending autosave timer to prevent crashes after disable
    try:
        from .core.autosave import _timer_cb
        import bpy
        if bpy.app.timers.is_registered(_timer_cb):
            bpy.app.timers.unregister(_timer_cb)
    except Exception:
        pass

    unregister_context_menu()

    # Remove only addon keyconfig items (user customizations persist separately)
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            try:
                if km and kmi and km.keymap_items:
                    km.keymap_items.remove(kmi)
            except Exception:
                pass

    addon_keymaps.clear()
    
    # Clear operator cache on addon disable
    try:
        from .ui.prefs import _clear_operator_cache
        _clear_operator_cache()
    except Exception:
        pass

    for cls in reversed(_classes):
        _safe_unregister_class(cls)
