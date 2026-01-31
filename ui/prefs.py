"""Addon preferences and property groups."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import os

import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .layout import draw_addon_preferences
from .nerd_icons import NERD_ICONS
from ..utils.addon_package import addon_root_package

# Module-level flag to suspend callbacks during bulk operations
# This persists across prefs object reinitializations
_SUSPEND_CALLBACKS = False

def _addon_root_pkg() -> str:
    """Return the root package used to look up prefs in Blender.

    - Extensions: "bl_ext.{repo}.{addon_id}"
    - Legacy: "{addon_id}"
    """
    return addon_root_package(__package__)

def default_config_path() -> str:
    """
    Default config path: Uses extension-specific user directory.
    This directory persists between extension upgrades.
    """
    # Use extension_path_user for extension-specific user directory (persists between upgrades)
    try:
        root_pkg = _addon_root_pkg()
        extension_dir = bpy.utils.extension_path_user(root_pkg, path="", create=True)
        if extension_dir:
            return os.path.join(extension_dir, "chordsong.json")
    except Exception:
        pass
    # Fallback to user_resource (respects BLENDER_USER_RESOURCES / BLENDER_USER_SCRIPTS)
    try:
        presets_dir = bpy.utils.user_resource("SCRIPTS", path="presets", create=True)
        if presets_dir:
            return os.path.join(presets_dir, "chordsong", "chordsong.json")
    except Exception:
        pass
    return ""

def save_config_path_persistent(config_path: str):
    """
    Save the config path to a persistent file.
    This allows the path to survive addon disable/enable and script reloads.
    """
    try:
        if hasattr(bpy.utils, 'extension_path_user'):
            root_pkg = _addon_root_pkg()
            extension_dir = bpy.utils.extension_path_user(root_pkg, path="", create=True)
            if extension_dir:
                config_path_file = os.path.join(extension_dir, "config_path.txt")
                os.makedirs(extension_dir, exist_ok=True)
                with open(config_path_file, "w", encoding="utf-8") as f:
                    f.write(config_path)
    except Exception:
        pass

def _autosave_now(prefs):
    # Best effort debounced autosave, used by property update callbacks.
    try:
        from ..core.autosave import schedule_autosave

        schedule_autosave(prefs, delay_s=5.0)
    except Exception:
        pass

def _check_conflicts_silent(context):
    """Run conflict checker without showing popup - just updates the conflicts cache."""
    try:
        from ..operators.check_conflicts import CHORDSONG_OT_CheckConflicts, find_conflicts
        prefs = context.preferences.addons[_addon_root_pkg()].preferences
        
        conflicts = find_conflicts(prefs.mappings)
        CHORDSONG_OT_CheckConflicts.conflicts = conflicts
    except Exception:
        pass

def _on_prefs_changed(self, _context):
    # Called when a preferences value changes.
    try:
        # Skip callbacks during bulk operations (config loading, etc.)
        if _SUSPEND_CALLBACKS:
            return
        
        self.ensure_defaults()
        _autosave_now(self)
    except Exception:
        pass

def _on_stats_interval_changed(self, _context):
    # Called when stats auto-export interval changes - restart the timer.
    try:
        # Skip callbacks during bulk operations (config loading, etc.)
        if _SUSPEND_CALLBACKS:
            return
        
        # Restart the stats auto-export timer with new interval
        from ..core.stats_manager import ChordSong_StatsManager
        
        # Signal existing timer(s) to stop on next run
        ChordSong_StatsManager.timer_should_stop = True
        
        # Unregister existing timer(s) - may not catch all if already scheduled
        try:
            while bpy.app.timers.is_registered(ChordSong_StatsManager.save_to_disk):
                bpy.app.timers.unregister(ChordSong_StatsManager.save_to_disk)
        except (ValueError, RuntimeError):
            pass
        
        # Re-register with new interval
        new_interval = float(self.stats_auto_export_interval)
        if new_interval <= 0:
            new_interval = 60.0  # Check every 60 seconds if disabled
        
        # Reset the stop flag before registering new timer
        ChordSong_StatsManager.timer_should_stop = False
        bpy.app.timers.register(ChordSong_StatsManager.save_to_disk, first_interval=new_interval)
        
        # Also call standard prefs changed
        _on_prefs_changed(self, _context)
    except Exception:
        pass

def _on_mapping_changed(_self, context):
    try:
        # Skip callbacks during bulk operations (config loading, etc.)
        if _SUSPEND_CALLBACKS:
            return
        
        prefs = context.preferences.addons[_addon_root_pkg()].preferences
        prefs.ensure_defaults()
        _autosave_now(prefs)
        
        # Clear overlay cache so changes appear immediately
        from .overlay import clear_overlay_cache
        clear_overlay_cache()
        
        # Sync groups after a short delay to avoid crashing during rapid typing/redraws
        prefs.sync_groups_delayed()
        
        # Check conflicts silently to update UI highlighting
        _check_conflicts_silent(context)
    except Exception:
        pass


def _on_group_changed(_self, context):
    # Called when a group item changes; fetch prefs via context.
    try:
        # Skip callbacks during bulk operations (config loading, etc.)
        if _SUSPEND_CALLBACKS:
            return
        
        prefs = context.preferences.addons[_addon_root_pkg()].preferences
        _autosave_now(prefs)
    except Exception:
        pass

def _group_search_callback(_self, context, _edit_text):
    try:
        pkg = _addon_root_pkg()
        prefs = context.preferences.addons[pkg].preferences
        return sorted([g.name for g in prefs.groups])
    except Exception:
        return []

# Cache for operator idnames to avoid rebuilding on every keystroke
_operator_cache = None

def clear_operator_cache():
    """Clear the operator cache. Useful when operators may have changed (addon enable/disable)."""
    global _operator_cache
    _operator_cache = None

def _build_operator_cache():
    """
    Build cached list of all operator idnames.
    
    Note: Cache persists until explicitly cleared. Operators registered/unregistered
    after cache creation won't appear until cache is cleared. This is acceptable
    since operator registration typically happens at addon enable time.
    """
    global _operator_cache
    try:
        # Return cached list if available
        if _operator_cache is not None:
            return _operator_cache
        
        operators = []
        seen = set()
        
        # Iterate through bpy.ops modules (most reliable method)
        # Cache module names to avoid repeated dir() calls
        try:
            op_modules = [name for name in dir(bpy.ops) if not name.startswith('_')]
        except Exception:
            # Fallback: return empty list if bpy.ops is not accessible
            return []
        
        for module_name in op_modules:
            try:
                op_module = getattr(bpy.ops, module_name)
                # Cache operator names per module
                op_names = [name for name in dir(op_module) if not name.startswith('_')]
                for op_name in op_names:
                    full_idname = f"{module_name}.{op_name}"
                    if full_idname not in seen:
                        operators.append(full_idname)
                        seen.add(full_idname)
            except (AttributeError, TypeError):
                # Skip modules that can't be accessed or aren't operator modules
                continue
            except Exception:
                # Skip any other errors to prevent one bad module from breaking everything
                continue
        
        _operator_cache = sorted(operators)
        return _operator_cache
    except Exception:
        # Return empty list on any error to prevent UI crashes
        return []

def _fuzzy_match_operator(query: str, operator_idname: str) -> tuple[bool, int]:
    """
    Fuzzy match query against operator idname using the existing fuzzy_match function.
    Normalizes dots and underscores to spaces before matching.
    """
    from ..utils.fuzzy import fuzzy_match
    
    # Normalize: treat dots and underscores as spaces (in addition to what fuzzy_match does)
    query_normalized = query.replace('.', ' ').replace('_', ' ')
    text_normalized = operator_idname.replace('.', ' ').replace('_', ' ')
    
    # Remove extra spaces
    query_normalized = ' '.join(query_normalized.split())
    text_normalized = ' '.join(text_normalized.split())
    
    # Use the existing fuzzy_match function
    return fuzzy_match(query_normalized, text_normalized)

def _operator_search_callback(_self, _context, edit_text):
    """
    Search callback for operator idname field - provides Blender's operator search.
    
    Returns a list of operator idnames matching the search text.
    Uses cached operator list for performance.
    Supports fuzzy matching: "add op" will match "addon.operator"
    """
    try:
        # Get cached operator list
        all_operators = _build_operator_cache()
        
        if not all_operators:
            # Return empty if cache building failed
            return []
        
        if not edit_text:
            # Return all operators if no search text (limited to prevent UI lag)
            # Limit to first 10 to prevent UI slowdown with very large lists
            return all_operators[:10]
        
        edit_text_clean = edit_text.strip()
        
        # Use fuzzy matching for better search experience
        matched_operators = []
        for op in all_operators:
            matched, score = _fuzzy_match_operator(edit_text_clean, op)
            if matched:
                matched_operators.append((score, op))
        
        # Sort by score (lower is better) and return just the operator names
        matched_operators.sort(key=lambda x: x[0])
        results = [op for _, op in matched_operators]
        
        # Limit results to prevent UI lag with very broad searches
        # 50 is a reasonable limit that still shows plenty of results
        return results[:50]
    except Exception:
        # Return empty list on any error to prevent UI crashes
        return []

class CHORDSONG_PG_NerdIcon(PropertyGroup):
    """Nerd Font icon definition for searchable dropdown."""
    name: StringProperty(
        name="Icon Name",
        description="Display name for the icon",
        default="",
    )
    icon: StringProperty(
        name="Icon Character",
        description="The actual Nerd Font icon character",
        default="",
    )

class CHORDSONG_PG_StatsItem(PropertyGroup):
    """Property group for a single statistics item."""
    name: StringProperty(
        name="Name",
        description="Operator/chord identifier",
        default="",
    )
    count: IntProperty(
        name="Count",
        description="Usage count",
        default=0,
        min=0,
    )
    category: StringProperty(
        name="Type",
        description="Category: operator or chord",
        default="",
    )
    group: StringProperty(
        name="Group",
        description="Group name (for chords only)",
        default="",
    )
    label: StringProperty(
        name="Label",
        description="Label name (for chords only)",
        default="",
    )

class CHORDSONG_PG_Group(PropertyGroup):
    """Group property for organizing chord mappings."""
    name: StringProperty(
        name="Group Name",
        description="Name of the group",
        default="",
        update=_on_group_changed,
    )
    icon: StringProperty(
        name="Icon",
        description="Nerd Fonts emoji/icon for this group (e.g. '', '', '', '')",
        default="",
        update=_on_group_changed,
    )
    display_order: IntProperty(
        name="Display Order",
        description="Order in which groups are displayed",
        default=0,
        options={'HIDDEN'},
    )
    expanded: BoolProperty(
        name="Expanded",
        description="Whether this group is expanded in the UI",
        default=False,
        update=_on_group_changed,
    )

class CHORDSONG_PG_SubItem(PropertyGroup):
    """Sub-item for multiple context actions."""
    path: StringProperty(
        name="Path",
        description="Context path (e.g. space_data.overlay.show_face_orientation)",
        default="",
        update=_on_mapping_changed,
    )
    value: StringProperty(
        name="Value",
        description="Property value (Python expression, only for CONTEXT_PROPERTY)",
        default="",
        update=_on_mapping_changed,
    )

class CHORDSONG_PG_OperatorParam(PropertyGroup):
    """Additional parameter row for operator mappings."""
    value: StringProperty(
        name="Value",
        description="Python-like parameter string: mode='ADD', factor=1.0",
        default="",
        update=_on_mapping_changed,
    )

class CHORDSONG_PG_SubOperator(PropertyGroup):
    """Sub-operator for consecutive operator calls."""
    operator: StringProperty(
        name="Operator",
        description="Blender operator id, e.g. 'view3d.view_selected'",
        default="",
        update=_on_mapping_changed,
        search=_operator_search_callback,
    )
    call_context: EnumProperty(
        name="Call Context",
        description="How to call the operator (invoke shows UI, exec runs immediately)",
        items=(
            ("EXEC_DEFAULT", "Exec", "Run the operator immediately"),
            ("INVOKE_DEFAULT", "Invoke", "Invoke the operator (may show UI)"),
        ),
        default="EXEC_DEFAULT",
        update=_on_mapping_changed,
    )
    kwargs_json: StringProperty(
        name="Parameters",
        description=(
            "Python-like parameters: use_all_regions = False, mode = \"EDIT\"\n"
            "Or full call: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, location=(0,0,0))"
        ),
        default="",
        update=_on_mapping_changed,
    )
    # Additional parameter rows for this operator call
    operator_params: CollectionProperty(type=CHORDSONG_PG_OperatorParam)

class CHORDSONG_PG_ScriptParam(PropertyGroup):
    """Parameter row for Python script mappings."""
    value: StringProperty(
        name="Value",
        description="Python-like parameter string: mode='ADD', factor=1.0",
        default="",
        update=_on_mapping_changed,
    )

class CHORDSONG_PG_Mapping(PropertyGroup):
    """Mapping property group for chord-to-action mappings."""

    order_index: IntProperty(
        name="Order Index",
        description="Explicit order index for manual sorting (lower = earlier)",
        default=0,
        min=0,
    )
    chord: StringProperty(
        name="Chord",
        description="Chord sequence, space-separated tokens (e.g. 'g g')",
        default="",
        update=_on_mapping_changed,
    )
    label: StringProperty(
        name="Label",
        description="Human-readable description shown in the which-key overlay",
        default="",
        update=_on_mapping_changed,
    )
    icon: StringProperty(
        name="Icon",
        description="Nerd Fonts emoji/icon for this chord (e.g. '', '', '', '')",
        default="",
        update=_on_mapping_changed,
    )
    group: StringProperty(
        name="Group",
        description="Optional category used to group items in UI and overlay",
        default="",
        update=_on_mapping_changed,
        search=_group_search_callback,
    )
    context: EnumProperty(
        name="Context",
        description="Editor context where this chord mapping is active",
        items=(
            ("ALL", "All Contexts", "Active in all editor contexts", "WORLD", 0),
            ("VIEW_3D", "3D View (Object)", "Active in 3D View (Object Mode)", "OBJECT_DATAMODE", 1),
            ("VIEW_3D_EDIT", "3D View (Edit)", "Active in 3D View (Edit Modes)", "EDITMODE_HLT", 2),
            ("GEOMETRY_NODE", "Geometry Nodes", "Active in Geometry Nodes editor", "GEOMETRY_NODES", 3),
            ("SHADER_EDITOR", "Shader Editor", "Active in Shader Editor", "NODE_MATERIAL", 4),
            ("IMAGE_EDITOR", "UV Editor", "Active in UV Editor", "UV", 5),
        ),
        default="VIEW_3D",
        update=_on_mapping_changed,
    )
    mapping_type: EnumProperty(
        name="Type",
        description="Type of action to execute",
        items=(
            ("OPERATOR", "Operator", "Blender operator ID", "SETTINGS", 0),
            ("PYTHON_FILE", "Script", "Execute a Python script file", "FILE_SCRIPT", 1),
            ("CONTEXT_TOGGLE", "Toggle", "Toggle a boolean property", "CHECKBOX_HLT", 2),
            ("CONTEXT_PROPERTY", "Property", "Set a property to a specific value", "PROPERTIES", 3),
        ),
        default="OPERATOR",
        update=_on_mapping_changed,
    )
    operator: StringProperty(
        name="Operator",
        description="Blender operator id, e.g. 'view3d.view_selected'",
        default="",
        update=_on_mapping_changed,
        search=_operator_search_callback,
    )
    python_file: StringProperty(
        name="Python File",
        description="Path to Python script file to execute",
        subtype="FILE_PATH",
        default="",
        update=_on_mapping_changed,
    )
    context_path: StringProperty(
        name="Context Path",
        description="Path to property to toggle or set (e.g. 'space_data.overlay.show_face_orientation')",
        default="",
        update=_on_mapping_changed,
    )
    property_value: StringProperty(
        name="Property Value",
        description="Value to set for the property (Python expression)",
        default="",
        update=_on_mapping_changed,
    )
    call_context: EnumProperty(
        name="Call Context",
        description="How to call the operator (invoke shows UI, exec runs immediately)",
        items=(
            ("EXEC_DEFAULT", "Exec", "Run the operator immediately"),
            ("INVOKE_DEFAULT", "Invoke", "Invoke the operator (may show UI)"),
        ),
        default="EXEC_DEFAULT",
        update=_on_mapping_changed,
    )
    kwargs_json: StringProperty(
        name="Parameters",
        description=(
            "Python-like parameters: use_all_regions = False, mode = \"EDIT\"\n"
            "Or full call: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, location=(0,0,0))"
        ),
        default="",
        update=_on_mapping_changed,
    )
    # Collection for multiple actions (Toggles or Properties)
    sub_items: CollectionProperty(type=CHORDSONG_PG_SubItem)
    # Collection for multiple consecutive operator calls
    sub_operators: CollectionProperty(type=CHORDSONG_PG_SubOperator)
    # Collection for multiple script parameters
    script_params: CollectionProperty(type=CHORDSONG_PG_ScriptParam)
    # Collection for multiple operator parameter rows (in addition to kwargs_json)
    operator_params: CollectionProperty(type=CHORDSONG_PG_OperatorParam)
    sync_toggles: BoolProperty(
        name="Sync Toggles",
        description="If enabled, all sub-item toggles will match the state of the primary toggle",
        default=False,
        update=_on_mapping_changed,
    )
    enabled: BoolProperty(name="Enabled", default=True, update=_on_mapping_changed)
    expanded: BoolProperty(
        name="Expanded",
        description="Whether this chord mapping is expanded in the UI",
        default=True,
        update=_on_mapping_changed,
    )
    selected: BoolProperty(
        name="Selected",
        description="Whether this chord mapping is selected for copy/paste operations",
        default=False,
    )

class CHORDSONG_Preferences(AddonPreferences):
    """Chord Song addon preferences."""

    bl_idname = _addon_root_pkg()

    prefs_tab: EnumProperty(
        name="Tab",
        items=(
            ("MAPPINGS", "Mappings", "Chord mappings"),
            ("UI", "UI", "Overlay/UI customization"),
            ("STATS", "Statistics", "Usage statistics"),
        ),
        default="MAPPINGS",
    )

    mapping_context_tab: EnumProperty(
        name="Mapping Context Tab",
        description="Select the editor context for chord mappings",
        items=(
            ("VIEW_3D", "3D View (Object)", "3D View (Object Mode) chord mappings"),
            ("VIEW_3D_EDIT", "3D View (Edit)", "3D View (Edit Modes) chord mappings"),
            ("GEOMETRY_NODE", "Geometry Nodes", "Geometry Nodes editor chord mappings"),
            ("SHADER_EDITOR", "Shader Editor", "Shader Editor chord mappings"),
            ("IMAGE_EDITOR", "UV Editor", "UV Editor chord mappings"),
        ),
        default="VIEW_3D",
    )

    selection_mode: BoolProperty(
        name="Selection Mode",
        description="Toggle selection mode for copying mappings",
        default=False,
    )

    config_path: StringProperty(
        name="Config Path",
        description="Optional JSON config file path (used as default for Load/Save)",
        subtype="FILE_PATH",
        default="",
        update=_on_prefs_changed,
    )

    scripts_folder: StringProperty(
        name="Scripts Folder",
        description="Folder containing custom Python scripts for quick selection",
        subtype="DIR_PATH",
        default="",
        update=_on_prefs_changed,
    )

    allow_custom_user_scripts: BoolProperty(
        name="Allow Custom User Scripts",
        description="Enable execution of custom Python scripts via chord mappings. "
                    "⚠️ Only enable this if you trust the scripts you're executing. "
                    "Scripts have full access to Blender's Python API.",
        default=False,
        update=_on_prefs_changed,
    )

    # Scripts Overlay Settings
    scripts_overlay_max_items: IntProperty(
        name="Scripts Overlay Max Items",
        description="Maximum number of scripts to show in the scripts overlay. "
                    "Note: Actual display is also limited by 'Overlay max items' setting above. "
                    "Only first 10 items get chord numbers (1-9, 0).",
        default=50,
        min=10,
        max=100,
        update=_on_prefs_changed,
    )
    scripts_overlay_gap: FloatProperty(
        name="Elements Gap",
        description="Gap between elements (icon, chord, label) in scripts overlay",
        default=5.0,
        min=0.0,
        max=100.0,
        update=_on_prefs_changed,
    )
    scripts_overlay_column_gap: FloatProperty(
        name="Column Gap",
        description="Gap between columns in scripts overlay",
        default=25.0,
        min=0.0,
        max=200.0,
        update=_on_prefs_changed,
    )
    scripts_overlay_max_label_length: IntProperty(
        name="Max Label Length",
        description="Maximum character length for script labels before truncation. Set to 0 for no limit.",
        default=0,
        min=0,
        max=200,
        update=_on_prefs_changed,
    )
    scripts_overlay_column_rows: IntProperty(
        name="Rows Per Column",
        description="Maximum number of rows per column in scripts overlay",
        default=10,
        min=1,
        max=100,
        update=_on_prefs_changed,
    )

    overlay_enabled: BoolProperty(
        name="Overlay",
        description="Show which-key style overlay while capturing chords",
        default=True,
        update=_on_prefs_changed,
    )
    overlay_fading_enabled: BoolProperty(
        name="Fading Overlay",
        description="Show notification overlay after command execution",
        default=True,
        update=_on_prefs_changed,
    )
    overlay_hide_panels: BoolProperty(
        name="Hide T & N Panels",
        description="Hide Tool (T) and Properties (N) panels while Leader key modal is active",
        default=True,
        update=_on_prefs_changed,
    )
    
    toggle_multi_modifier: EnumProperty(
        name="Multi-Toggle Modifier",
        description="Hold this modifier while executing a toggle to keep overlay open for multiple toggles",
        items=[
            ('CTRL', "Ctrl", "Hold Ctrl to execute multiple toggles"),
            ('ALT', "Alt", "Hold Alt to execute multiple toggles"),
            ('SHIFT', "Shift", "Hold Shift to execute multiple toggles"),
        ],
        default='CTRL',
        update=_on_prefs_changed,
    )
    overlay_max_items: IntProperty(
        name="Overlay max items",
        default=50,
        min=1,
        max=100,
        update=_on_prefs_changed,
    )
    overlay_column_rows: IntProperty(
        name="Column rows",
        description=(
            "Maximum number of rows per column in the overlay "
            "before wrapping to the next column"
        ),
        default=8,
        min=1,
        max=60,
        update=_on_prefs_changed,
    )

    overlay_sort_mode: EnumProperty(
        name="Overlay Sorting",
        description="How to prioritize chords in the overlay list",
        items=(
            ("GROUP_AND_INDEX", "Group + Order", "Use group order (Mappings tab) and manual chord order within each group"),
            ("LABEL", "Label", "Sort alphabetically by label (natural sorting)"),
            ("CHORD", "Chord", "Sort by chord token (natural sorting: 2 before 10)"),
        ),
        default="GROUP_AND_INDEX",
        update=_on_prefs_changed,
    )

    overlay_font_size_header: IntProperty(
        name="Header font size",
        default=16,
        min=8,
        max=72,
        update=_on_prefs_changed,
    )
    overlay_font_size_chord: IntProperty(
        name="Chord font size",
        description="Font size for chord tokens (keys) in the overlay",
        default=16,
        min=8,
        max=72,
        update=_on_prefs_changed,
    )
    overlay_font_size_body: IntProperty(
        name="Body font size",
        default=15,
        min=8,
        max=72,
        update=_on_prefs_changed,
    )
    overlay_font_size_footer: IntProperty(
        name="Footer font size",
        default=12,
        min=8,
        max=72,
        update=_on_prefs_changed,
    )
    overlay_font_size_fading: IntProperty(
        name="Fading Overlay Size",
        description="Font size for fading result overlay",
        default=24,
        min=8,
        max=96,
        update=_on_prefs_changed,
    )
    overlay_font_size_toggle: IntProperty(
        name="Toggle Icon Size",
        description="Font size for toggle switch icons in overlay",
        default=23,
        min=4,
        max=48,
        update=_on_prefs_changed,
    )
    overlay_toggle_offset_y: IntProperty(
        name="Toggle Y Offset",
        description="Vertical offset for toggle switch icons",
        default=-4,
        min=-50,
        max=50,
        update=_on_prefs_changed,
    )
    overlay_font_size_separator: IntProperty(
        name="Separator Size",
        description="Font size for separator characters (→, ::, etc.)",
        default=15,
        min=4,
        max=72,
        update=_on_prefs_changed,
    )

    overlay_show_header: BoolProperty(
        name="Show Header",
        description="Show the overlay header bar",
        default=True,
        update=_on_prefs_changed,
    )
    overlay_show_footer: BoolProperty(
        name="Show Footer",
        description="Show the overlay footer bar",
        default=True,
        update=_on_prefs_changed,
    )

    overlay_color_chord: FloatVectorProperty(
        name="Chord color",
        description="Color for chord tokens (keys)",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.65, 0.80, 1.00, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_label: FloatVectorProperty(
        name="Label color",
        description="Color for chord descriptions",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.00, 1.00, 1.00, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_header: FloatVectorProperty(
        name="Header color",
        description="Color for overlay header text",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.00, 1.00, 1.00, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_icon: FloatVectorProperty(
        name="Icon color",
        description="Color for Nerd Font icons",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.80, 0.80, 0.80, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_toggle_on: FloatVectorProperty(
        name="Toggle ON color",
        description="Color for toggle indicator when state is ON",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.65, 0.80, 1.00, 0.40),
        update=_on_prefs_changed,
    )
    overlay_color_toggle_off: FloatVectorProperty(
        name="Toggle OFF color",
        description="Color for toggle indicator when state is OFF",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.00, 1.00, 1.00, 0.20),
        update=_on_prefs_changed,
    )
    overlay_color_recents_hotkey: FloatVectorProperty(
        name="Recents hotkey color",
        description="Color for hotkey numbers/letters in the Recents list",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.65, 0.80, 1.00, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_separator: FloatVectorProperty(
        name="Separator color",
        description="Color for separator tokens (→, ::, etc.)",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.00, 1.00, 1.00, 0.20),
        update=_on_prefs_changed,
    )
    overlay_color_group: FloatVectorProperty(
        name="Group color",
        description="Color for group names in overlay",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.90, 0.90, 0.50, 1.00),
        update=_on_prefs_changed,
    )
    overlay_color_counter: FloatVectorProperty(
        name="Counter color",
        description="Color for keymap counter (+N keymaps)",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.80, 0.80, 0.80, 0.80),
        update=_on_prefs_changed,
    )
    overlay_list_background: FloatVectorProperty(
        name="List background",
        description="Background color for the chords list area",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.35),
        update=_on_prefs_changed,
    )
    overlay_header_background: FloatVectorProperty(
        name="Header background",
        description="Background color for the header area",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.35),
        update=_on_prefs_changed,
    )
    overlay_footer_background: FloatVectorProperty(
        name="Footer background",
        description="Background color for the footer area",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.35),
        update=_on_prefs_changed,
    )

    overlay_position: EnumProperty(
        name="Position",
        description="Overlay anchor position in the viewport",
        items=(
            ("TOP_LEFT", "Top Left", ""),
            ("TOP_RIGHT", "Top Right", ""),
            ("BOTTOM_LEFT", "Bottom Left", ""),
            ("BOTTOM_RIGHT", "Bottom Right", ""),
            ("CENTER_TOP", "Center Top", ""),
            ("CENTER_BOTTOM", "Center Bottom", ""),
        ),
        default="BOTTOM_LEFT",
        update=_on_prefs_changed,
    )
    overlay_offset_x: IntProperty(
        name="Offset X",
        default=65,
        min=-2000,
        max=2000,
        update=_on_prefs_changed,
    )
    overlay_offset_y: IntProperty(
        name="Offset Y",
        default=-15,
        min=-2000,
        max=2000,
        update=_on_prefs_changed,
    )

    overlay_gap: IntProperty(
        name="Element Gap",
        description="Gap between icon, chord, and label elements",
        default=10,
        min=-50,
        max=100,
        update=_on_prefs_changed,
    )
    overlay_column_gap: IntProperty(
        name="Column Gap",
        description="Gap between columns",
        default=100,
        min=-100,
        max=200,
        update=_on_prefs_changed,
    )
    overlay_line_height: FloatProperty(
        name="Line Height",
        description="Line height multiplier (relative to body font size)",
        default=1.5,
        min=1.0,
        max=3.0,
        update=_on_prefs_changed,
    )
    overlay_footer_gap: IntProperty(
        name="Footer Gap",
        description="Gap between footer items",
        default=50,
        min=-50,
        max=200,
        update=_on_prefs_changed,
    )
    overlay_footer_token_gap: IntProperty(
        name="Footer Token Gap",
        description="Gap between token and icon/label in footer",
        default=4,
        min=-50,
        max=100,
        update=_on_prefs_changed,
    )
    overlay_footer_label_gap: IntProperty(
        name="Footer Label Gap",
        description="Gap between icon and label in footer",
        default=8,
        min=-50,
        max=100,
        update=_on_prefs_changed,
    )

    overlay_item_format: EnumProperty(
        name="Overlay Style",
        description="Choose how folder/summary items (prefixes leading to multiple actions) are displayed",
        items=(
            ("DEFAULT", "Default: → +N keymaps", "Classic count-only style"),
            ("CUSTOM", "Custom Format", "Use custom format string"),
        ),
        default="DEFAULT",
        update=_on_prefs_changed,
    )
    
    # Custom format strings
    overlay_format_folder: StringProperty(
        name="Folder Format",
        description=(
            "Custom format for folder items (multiple keymaps)\n"
            "Tokens: I=Icon, C=Chord, G=All Groups, g=First Group, L=Label, N=Verbose Count (+3 keymaps), n=Compact Count (+3), S=Separator A, s=Separator B"
        ),
        default="C n s G L",
        update=_on_prefs_changed,
    )
    
    overlay_format_item: StringProperty(
        name="Item Format",
        description=(
            "Custom format for single items\n"
            "Tokens: I=Icon, C=Chord, G=All Groups, g=First Group, L=Label, S=Separator A, s=Separator B, T=Toggle"
        ),
        default="C I S L T",
        update=_on_prefs_changed,
    )
    
    overlay_separator_a: StringProperty(
        name="Separator A",
        description="Primary separator (used by S token)",
        default="→",
        update=_on_prefs_changed,
    )
    
    overlay_separator_b: StringProperty(
        name="Separator B", 
        description="Secondary separator (used by s token)",
        default="::",
        update=_on_prefs_changed,
    )
    
    overlay_max_label_length: IntProperty(
        name="Max Label Length",
        description="Maximum character length for labels before truncation. The longest label in each column sets the width for toggle icon alignment. Set to 0 for no limit.",
        default=0,
        min=0,
        max=200,
        update=_on_prefs_changed,
    )

    mappings: CollectionProperty(type=CHORDSONG_PG_Mapping)
    groups: CollectionProperty(type=CHORDSONG_PG_Group)
    nerd_icons: CollectionProperty(type=CHORDSONG_PG_NerdIcon)

    ungrouped_expanded: BoolProperty(
        name="Ungrouped Expanded",
        description="Whether the Ungrouped section is expanded",
        default=False,
        update=_on_prefs_changed,
    )

    chord_search: StringProperty(
        name="Chord Search",
        description="Search chords by chord, label, operator, property, toggle, or script",
        default="",
        update=_on_prefs_changed,
    )

    # Statistics properties
    enable_stats: BoolProperty(
        name="Enable Statistics",
        description="Track operator and chord usage. Data is stored locally and never shared.",
        default=False,
        update=_on_prefs_changed,
    )
    
    stats_collection: CollectionProperty(type=CHORDSONG_PG_StatsItem)
    
    stats_collection_index: IntProperty(
        name="Stats Collection Index",
        description="Active index in statistics collection",
        default=0,
        min=0,
    )
    
    stats_sort_by_usage: BoolProperty(
        name="Sort by Usage",
        description="Sort statistics by usage count (descending). If disabled, sorts alphabetically.",
        default=True,
        update=_on_prefs_changed,
    )
    
    stats_export_path: StringProperty(
        name="Export Path",
        description="Path to export statistics JSON file",
        subtype="FILE_PATH",
        default="",
    )
    
    stats_auto_export_interval: IntProperty(
        name="Auto Export Interval",
        description="Interval in seconds for automatically saving statistics to disk (0 = disabled)",
        default=180,
        min=0,
        soft_max=3600,
        update=_on_stats_interval_changed,
    )
    
    stats_blacklist: StringProperty(
        name="Statistics Blacklist",
        description="JSON array of blacklisted items in format: [\"category:name\", ...]",
        default="[]",
    )

    def ensure_defaults(self):
        """Ensure default config path and nerd icons are initialized."""
        # Only set config_path if it's truly empty (first time setup)
        # Blender persists this value automatically, so we shouldn't overwrite it
        if not (self.config_path or "").strip():
            self.config_path = default_config_path()
        
        # Auto-assign stats export path if empty (same directory as config)
        if not (self.stats_export_path or "").strip():
            config_path = self.config_path or default_config_path()
            if config_path:
                config_dir = os.path.dirname(config_path)
                self.stats_export_path = os.path.join(config_dir, "chordsong_stats.json")
                # Persist the path like we do with config_path
                try:
                    import bpy
                    pkg = _addon_root_pkg()
                    if hasattr(bpy.utils, 'extension_path_user'):
                        extension_dir = bpy.utils.extension_path_user(pkg, path="", create=True)
                        if extension_dir:
                            stats_path_file = os.path.join(extension_dir, "stats_export_path.txt")
                            os.makedirs(extension_dir, exist_ok=True)
                            with open(stats_path_file, "w", encoding="utf-8") as f:
                                f.write(self.stats_export_path)
                except Exception:
                    pass

        # Ensure custom scripts are disabled by default (security safeguard)
        if not hasattr(self, "allow_custom_user_scripts") or self.allow_custom_user_scripts is None:
            self.allow_custom_user_scripts = False

        # Populate nerd icons
        self._populate_nerd_icons()

    # Static variable to hold the timer function for debouncing
    _sync_timer_fn = None

    def sync_groups_delayed(self, remove_unused=False):
        """Schedule a group sync to run outside of the current UI/Draw cycle (Debounced)."""
        # Remove old timer if it exists to avoid piling up
        if CHORDSONG_Preferences._sync_timer_fn:
            if bpy.app.timers.is_registered(CHORDSONG_Preferences._sync_timer_fn):
                bpy.app.timers.unregister(CHORDSONG_Preferences._sync_timer_fn)
        
        def run_sync():
            try:
                # We need to re-fetch prefs since self might be invalid if reloaded
                prefs = bpy.context.preferences.addons[_addon_root_pkg()].preferences
                prefs._sync_groups_from_mappings(remove_unused=remove_unused)
            except Exception:
                pass
            CHORDSONG_Preferences._sync_timer_fn = None
            return None

        CHORDSONG_Preferences._sync_timer_fn = run_sync
        bpy.app.timers.register(run_sync, first_interval=0.1)

    def _populate_nerd_icons(self):
        """Populate the nerd_icons collection with Blender/3D-relevant Nerd Font icons."""
        if self.nerd_icons:
            return  # Already populated

        for name, icon_char in NERD_ICONS:
            icon_item = self.nerd_icons.add()
            icon_item.name = name
            icon_item.icon = icon_char

    def _sync_groups_from_mappings(self, remove_unused=False):
        """
        Sync the groups collection with all groups found in mappings.
        Ensures that manually created groups and typed group names are both preserved.
        """
        # 1. Collect all names used in mappings
        used_names = set()
        for m in self.mappings:
            name = (getattr(m, "group", "") or "").strip()
            if name:
                used_names.add(name)
        
        # 2. Collect current names in the groups collection
        existing_names = {grp.name for grp in self.groups if grp.name}
        
        # 3. Determine changes
        to_add = used_names - existing_names
        to_remove = set()
        if remove_unused:
            to_remove = existing_names - used_names
        
        # 4. Apply changes surgically
        has_changes = False
        
        # Removing first (reverse order to preserve indices)
        if to_remove:
            for i in range(len(self.groups) - 1, -1, -1):
                if self.groups[i].name in to_remove:
                    self.groups.remove(i)
                    has_changes = True

        # Adding missing ones
        for name in to_add:
            grp = self.groups.add()
            grp.name = name
            has_changes = True

        # 5. Full rebuild (sorting) only if we had changes or explicitly requested
        if remove_unused or has_changes:
            self._sort_groups()

    def _sort_groups(self):
        """Preserve user-defined group order (no longer auto-sorts).
        
        Previously sorted alphabetically, but now users can manually 
        reorder groups with up/down buttons. New groups are added at the end.
        """
        # No longer auto-sort - preserve user order
        # This method is kept for API compatibility but is now a no-op
        pass

    def draw(self, context: bpy.types.Context):
        """Draw preferences UI."""
        draw_addon_preferences(self, context, self.layout)
