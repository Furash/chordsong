# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy
import os
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatVectorProperty,
    IntProperty,
    StringProperty,
)

from .layout import draw_addon_preferences


def _addon_root_pkg() -> str:
    # This module lives under "chordsong.ui", but AddonPreferences bl_idname must be "chordsong".
    return __package__.split(".")[0]


def default_config_path() -> str:
    """
    Default config path: <user scripts>/presets/chordsong/chordsong.json
    Uses Blender's user script resource location.
    """
    presets_dir = bpy.utils.user_resource("SCRIPTS", path="presets", create=True)
    if presets_dir:
        # Keep addon presets isolated in their own folder.
        return os.path.join(presets_dir, "chordsong", "chordsong.json")
    return ""


def _autosave_now(prefs):
    # Best effort debounced autosave, used by property update callbacks.
    try:
        from ..core.autosave import schedule_autosave

        schedule_autosave(prefs, delay_s=5.0)
    except Exception:
        pass


def _on_prefs_changed(self, _context):
    # Called when a preferences value changes.
    try:
        self.ensure_defaults()
        _autosave_now(self)
    except Exception:
        pass


def _on_mapping_changed(_self, context):
    # Called when a mapping item changes; fetch prefs via context.
    try:
        prefs = context.preferences.addons[_addon_root_pkg()].preferences
        prefs.ensure_defaults()
        _autosave_now(prefs)
    except Exception:
        pass
class CHORDSONG_PG_Mapping(PropertyGroup):
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
    group: StringProperty(
        name="Group",
        description="Optional category used to group items in UI and overlay",
        default="",
        update=_on_mapping_changed,
    )
    mapping_type: EnumProperty(
        name="Type",
        description="Type of action to execute",
        items=(
            ("OPERATOR", "Operator", "Blender operator ID"),
            ("PYTHON_FILE", "Python File", "Execute a Python script file"),
        ),
        default="OPERATOR",
        update=_on_mapping_changed,
    )
    operator: StringProperty(
        name="Operator",
        description="Blender operator id, e.g. 'view3d.view_selected'",
        default="",
        update=_on_mapping_changed,
    )
    python_file: StringProperty(
        name="Python File",
        description="Path to Python script file to execute",
        subtype="FILE_PATH",
        default="",
        update=_on_mapping_changed,
    )
    call_context: EnumProperty(
        name="Call Context",
        description="How to call the operator (invoke shows UI, exec runs immediately)",
        items=(
            ("EXEC_DEFAULT", "Exec Default", "Run the operator immediately"),
            ("INVOKE_DEFAULT", "Invoke Default", "Invoke the operator (may show UI)"),
        ),
        default="EXEC_DEFAULT",
        update=_on_mapping_changed,
    )
    kwargs_json: StringProperty(
        name="Parameters",
        description="Python-like parameters: use_all_regions = False, mode = \"EDIT\"\nOr full call: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, location=(0,0,0))",
        default="",
        update=_on_mapping_changed,
    )
    enabled: BoolProperty(name="Enabled", default=True, update=_on_mapping_changed)


class CHORDSONG_Preferences(AddonPreferences):
    bl_idname = _addon_root_pkg()

    prefs_tab: EnumProperty(
        name="Tab",
        items=(
            ("MAPPINGS", "Mappings", "Chord mappings"),
            ("UI", "UI", "Overlay/UI customization"),
        ),
        default="MAPPINGS",
    )

    config_path: StringProperty(
        name="Config Path",
        description="Optional JSON config file path (used as default for Load/Save)",
        subtype="FILE_PATH",
        default="",
        update=_on_prefs_changed,
    )

    timeout_ms: IntProperty(
        name="Chord Timeout (ms)",
        description="Cancel chord capture if idle for this many milliseconds",
        default=600,
        min=0,
        max=30_000,
        update=_on_prefs_changed,
    )
    overlay_enabled: BoolProperty(
        name="Overlay",
        description="Show which-key style overlay while capturing chords",
        default=True,
        update=_on_prefs_changed,
    )
    overlay_max_items: IntProperty(
        name="Overlay max items",
        default=14,
        min=1,
        max=60,
        update=_on_prefs_changed,
    )
    overlay_column_rows: IntProperty(
        name="Column rows",
        description="Maximum number of rows per column in the overlay before wrapping to the next column",
        default=12,
        min=3,
        max=60,
        update=_on_prefs_changed,
    )

    overlay_font_size_header: IntProperty(
        name="Header font size",
        default=18,
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
        default=14,
        min=8,
        max=72,
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

    overlay_position: EnumProperty(
        name="Position",
        description="Overlay anchor position in the viewport",
        items=(
            ("TOP_LEFT", "Top Left", ""),
            ("TOP_RIGHT", "Top Right", ""),
            ("BOTTOM_LEFT", "Bottom Left", ""),
            ("BOTTOM_RIGHT", "Bottom Right", ""),
        ),
        default="BOTTOM_LEFT",
        update=_on_prefs_changed,
    )
    overlay_offset_x: IntProperty(
        name="Offset X",
        default=14,
        min=0,
        max=2000,
        update=_on_prefs_changed,
    )
    overlay_offset_y: IntProperty(
        name="Offset Y",
        default=14,
        min=0,
        max=2000,
        update=_on_prefs_changed,
    )

    mappings: CollectionProperty(type=CHORDSONG_PG_Mapping)

    def ensure_defaults(self):
        if not (self.config_path or "").strip():
            self.config_path = default_config_path()

        if self.mappings:
            return

        def add(chord, label, group, operator, kwargs_json=""):
            m = self.mappings.add()
            m.chord = chord
            m.label = label
            m.group = group
            m.mapping_type = "OPERATOR"
            m.operator = operator
            m.call_context = "EXEC_DEFAULT"
            m.kwargs_json = kwargs_json
            m.enabled = True

        add("g g", "Frame Selected", "View", "view3d.view_selected", '{"use_all_regions": false}')
        add("g a", "Frame All", "View", "view3d.view_all", "{}")
        add("s r", "Run Active Script", "Script", "text.run_script", "{}")
        add("k c", "Open Preferences", "Chord Song", "chordsong.open_prefs", "{}")

    def draw(self, context: bpy.types.Context):
        draw_addon_preferences(self, context, self.layout)


