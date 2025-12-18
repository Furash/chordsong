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


def _addon_root_pkg() -> str:
    # This module lives under "chordsong.ui", but AddonPreferences bl_idname must be "chordsong".
    return __package__.split(".", maxsplit=1)[0]


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


def _on_group_changed(_self, context):
    # Called when a group item changes; fetch prefs via context.
    try:
        prefs = context.preferences.addons[_addon_root_pkg()].preferences
        _autosave_now(prefs)
    except Exception:
        pass


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


class CHORDSONG_PG_Group(PropertyGroup):
    """Group property for organizing chord mappings."""
    name: StringProperty(
        name="Group Name",
        description="Name of the group",
        default="",
        update=_on_group_changed,
    )
    display_order: IntProperty(
        name="Display Order",
        description="Order in which groups are displayed",
        default=0,
    )
    expanded: BoolProperty(
        name="Expanded",
        description="Whether this group is expanded in the UI",
        default=False,
    )


class CHORDSONG_PG_Mapping(PropertyGroup):
    """Mapping property group for chord-to-action mappings."""

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
    )
    context: EnumProperty(
        name="Context",
        description="Editor context where this chord mapping is active",
        items=(
            ("VIEW_3D", "3D View", "Active in 3D View editor"),
            ("GEOMETRY_NODE", "Geometry Nodes", "Active in Geometry Nodes editor"),
            ("SHADER_EDITOR", "Shader Editor", "Active in Shader Editor"),
            ("IMAGE_EDITOR", "UV Editor", "Active in UV Editor"),
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
    context_path: StringProperty(
        name="Context Path",
        description="Path to boolean property to toggle (e.g. 'space_data.overlay.show_face_orientation')",
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
        description=(
            "Python-like parameters: use_all_regions = False, mode = \"EDIT\"\n"
            "Or full call: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, location=(0,0,0))"
        ),
        default="",
        update=_on_mapping_changed,
    )
    enabled: BoolProperty(name="Enabled", default=True, update=_on_mapping_changed)


class CHORDSONG_Preferences(AddonPreferences):
    """Chord Song addon preferences."""

    bl_idname = _addon_root_pkg()

    prefs_tab: EnumProperty(
        name="Tab",
        items=(
            ("MAPPINGS", "Mappings", "Chord mappings"),
            ("UI", "UI", "Overlay/UI customization"),
        ),
        default="MAPPINGS",
    )
    
    mapping_context_tab: EnumProperty(
        name="Mapping Context Tab",
        description="Select the editor context for chord mappings",
        items=(
            ("VIEW_3D", "3D View", "3D View editor chord mappings"),
            ("GEOMETRY_NODE", "Geometry Nodes", "Geometry Nodes editor chord mappings"),
            ("SHADER_EDITOR", "Shader Editor", "Shader Editor chord mappings"),
            ("IMAGE_EDITOR", "UV Editor", "UV Editor chord mappings"),
        ),
        default="VIEW_3D",
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
        max=100,
        update=_on_prefs_changed,
    )
    overlay_column_rows: IntProperty(
        name="Column rows",
        description=(
            "Maximum number of rows per column in the overlay "
            "before wrapping to the next column"
        ),
        default=12,
        min=1,
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
    overlay_color_icon: FloatVectorProperty(
        name="Icon color",
        description="Color for Nerd Font icons",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(0.80, 0.80, 0.80, 0.70),
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
        default=14,
        min=-2000,
        max=2000,
        update=_on_prefs_changed,
    )
    overlay_offset_y: IntProperty(
        name="Offset Y",
        default=14,
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
        default=30,
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
        default=20,
        min=-50,
        max=200,
        update=_on_prefs_changed,
    )
    overlay_footer_token_gap: IntProperty(
        name="Footer Token Gap",
        description="Gap between token and icon/label in footer",
        default=10,
        min=-50,
        max=100,
        update=_on_prefs_changed,
    )
    overlay_footer_label_gap: IntProperty(
        name="Footer Label Gap",
        description="Gap between icon and label in footer",
        default=10,
        min=-50,
        max=100,
        update=_on_prefs_changed,
    )

    mappings: CollectionProperty(type=CHORDSONG_PG_Mapping)
    groups: CollectionProperty(type=CHORDSONG_PG_Group)
    nerd_icons: CollectionProperty(type=CHORDSONG_PG_NerdIcon)
    
    ungrouped_expanded: BoolProperty(
        name="Ungrouped Expanded",
        description="Whether the Ungrouped section is expanded",
        default=False,
    )

    def ensure_defaults(self):
        """Ensure default config path and mappings are set."""
        if not (self.config_path or "").strip():
            self.config_path = default_config_path()

        # Populate nerd icons
        self._populate_nerd_icons()

        # Sync groups from mappings
        self._sync_groups_from_mappings()

        if self.mappings:
            return

        def add(chord, label, group, operator, kwargs_json="", context="VIEW_3D"):
            m = self.mappings.add()
            m.chord = chord
            m.label = label
            m.group = group
            m.context = context
            m.mapping_type = "OPERATOR"
            m.operator = operator
            m.call_context = "EXEC_DEFAULT"
            m.kwargs_json = kwargs_json
            m.enabled = True

        add("g g", "Frame Selected", "View", "view3d.view_selected", '{"use_all_regions": false}', "VIEW_3D")
        add("g a", "Frame All", "View", "view3d.view_all", "{}", "VIEW_3D")
        add("s r", "Run Active Script", "Script", "text.run_script", "{}", "VIEW_3D")
        add("k c", "Open Preferences", "Chord Song", "chordsong.open_prefs", "{}", "VIEW_3D")

        # Sync groups after adding default mappings
        self._sync_groups_from_mappings()

    def _populate_nerd_icons(self):
        """Populate the nerd_icons collection with Blender/3D-relevant Nerd Font icons."""
        if self.nerd_icons:
            return  # Already populated

        for name, icon_char in NERD_ICONS:
            icon_item = self.nerd_icons.add()
            icon_item.name = name
            icon_item.icon = icon_char

    def _sync_groups_from_mappings(self):
        """
        Extract unique groups from mappings and populate groups collection.

        Also removes duplicate groups.
        """
        # First, remove duplicate groups from the groups collection
        seen_names = set()
        indices_to_remove = []

        for idx, grp in enumerate(self.groups):
            name = grp.name.strip() if grp.name else ""
            if not name or name in seen_names:
                # Empty name or duplicate - mark for removal
                indices_to_remove.append(idx)
            else:
                seen_names.add(name)

        # Remove duplicates in reverse order to maintain indices
        for idx in reversed(indices_to_remove):
            self.groups.remove(idx)

        # Get unique group names from mappings
        unique_groups = set()
        for m in self.mappings:
            group_name = (getattr(m, "group", "") or "").strip()
            if group_name:
                unique_groups.add(group_name)

        # Get existing group names (after duplicate removal)
        existing_groups = {grp.name for grp in self.groups}

        # Add new groups that don't exist yet
        for group_name in sorted(unique_groups - existing_groups):
            grp = self.groups.add()
            grp.name = group_name

    def draw(self, context: bpy.types.Context):
        """Draw preferences UI."""
        draw_addon_preferences(self, context, self.layout)
