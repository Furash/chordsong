"""Overlay theme preset operators."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

import json
import os
import bpy  # type: ignore
from bpy.props import StringProperty  # type: ignore
from ..common import prefs


class CHORDSONG_OT_ExportOverlayTheme(bpy.types.Operator):
    """Export current overlay theme colors to a JSON file"""

    bl_idname = "chordsong.export_overlay_theme"
    bl_label = "Export Overlay Theme"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        name="File Path",
        description="Path to save the theme",
        subtype='FILE_PATH',
        default="",
    )

    filename: StringProperty(
        name="File Name",
        default="chordsong_theme.json",
    )

    def invoke(self, context, event):
        # Set default filename
        if not self.filepath:
            self.filepath = self.filename
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        p = prefs(context)

        # Collect all overlay color properties
        theme_data = {
            "name": "Custom Theme",
            "description": "Exported overlay theme",
            "colors": {
                "chord": list(p.overlay_color_chord),
                "label": list(p.overlay_color_label),
                "header": list(p.overlay_color_header),
                "icon": list(p.overlay_color_icon),
                "group": list(p.overlay_color_group),
                "counter": list(p.overlay_color_counter),
                "toggle_on": list(p.overlay_color_toggle_on),
                "toggle_off": list(p.overlay_color_toggle_off),
                "recents_hotkey": list(p.overlay_color_recents_hotkey),
                "separator": list(p.overlay_color_separator),
                "list_background": list(p.overlay_list_background),
                "header_background": list(p.overlay_header_background),
                "footer_background": list(p.overlay_footer_background),
            }
        }

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2)
            self.report({'INFO'}, f"Theme exported to {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export theme: {e}")
            return {'CANCELLED'}


class CHORDSONG_OT_ImportOverlayTheme(bpy.types.Operator):
    """Import overlay theme colors from a JSON file"""

    bl_idname = "chordsong.import_overlay_theme"
    bl_label = "Import Overlay Theme"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: StringProperty(
        name="File Path",
        description="Path to the theme file",
        subtype='FILE_PATH',
        default="",
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        p = prefs(context)

        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)

            colors = theme_data.get("colors", {})

            # Apply colors to preferences
            if "chord" in colors:
                p.overlay_color_chord = colors["chord"]
            if "label" in colors:
                p.overlay_color_label = colors["label"]
            if "header" in colors:
                p.overlay_color_header = colors["header"]
            if "icon" in colors:
                p.overlay_color_icon = colors["icon"]
            if "group" in colors:
                p.overlay_color_group = colors["group"]
            if "counter" in colors:
                p.overlay_color_counter = colors["counter"]
            if "toggle_on" in colors:
                p.overlay_color_toggle_on = colors["toggle_on"]
            if "toggle_off" in colors:
                p.overlay_color_toggle_off = colors["toggle_off"]
            if "recents_hotkey" in colors:
                p.overlay_color_recents_hotkey = colors["recents_hotkey"]
            if "separator" in colors:
                p.overlay_color_separator = colors["separator"]
            if "list_background" in colors:
                p.overlay_list_background = colors["list_background"]
            if "header_background" in colors:
                p.overlay_header_background = colors["header_background"]
            if "footer_background" in colors:
                p.overlay_footer_background = colors["footer_background"]

            theme_name = theme_data.get("name", "Imported Theme")
            self.report({'INFO'}, f"Theme '{theme_name}' imported successfully")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to import theme: {e}")
            return {'CANCELLED'}


class CHORDSONG_OT_ExtractBlenderTheme(bpy.types.Operator):
    """Extract overlay colors from current Blender theme"""

    bl_idname = "chordsong.extract_blender_theme"
    bl_label = "Match Current Blender Theme"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = prefs(context)
        theme = context.preferences.themes[0]

        def safe_getattr(obj, *attrs, default=None):
            """Safely get nested attributes, returning default if any don't exist."""
            for attr in attrs:
                try:
                    obj = getattr(obj, attr)
                except AttributeError:
                    return default
            return obj

        def srgb_to_linear(c):
            """Convert sRGB component to linear space."""
            if c <= 0.04045:
                return c / 12.92
            else:
                return ((c + 0.055) / 1.055) ** 2.4

        try:
            # Extract colors from current Blender theme
            view3d = theme.view_3d
            ui = theme.user_interface

            # Chord color and recents key: ThemeView3D.face_select
            if face_select := safe_getattr(view3d, 'face_select'):
                chord_color = [srgb_to_linear(face_select[0]), srgb_to_linear(face_select[1]), srgb_to_linear(face_select[2]), 1.0]
                p.overlay_color_chord = chord_color
                p.overlay_color_recents_hotkey = chord_color

            # Label, icon, header: ThemeUserInterface.wcol_regular.text
            separator_color = None
            label_color = None
            if wcol_regular := safe_getattr(ui, 'wcol_regular'):
                if text := safe_getattr(wcol_regular, 'text'):
                    label_color = [srgb_to_linear(text[0]), srgb_to_linear(text[1]), srgb_to_linear(text[2]), 1.0]
                    p.overlay_color_label = label_color
                    p.overlay_color_header = label_color
                    p.overlay_color_icon = label_color
                    
                    # Separator: same as label but with 20% alpha
                    separator_color = [srgb_to_linear(text[0]), srgb_to_linear(text[1]), srgb_to_linear(text[2]), 0.20]
                    p.overlay_color_separator = separator_color

            # List background: ThemeSpaceGeneric.back
            if space_generic := safe_getattr(theme, 'preferences'):
                if space := safe_getattr(space_generic, 'space'):
                    if back := safe_getattr(space, 'back'):
                        bg_color = [srgb_to_linear(back[0]), srgb_to_linear(back[1]), srgb_to_linear(back[2]), 1.0]
                        p.overlay_list_background = bg_color

                    # Header and footer: ThemeSpaceGeneric.header (50% darker)
                    if header := safe_getattr(space, 'header'):
                        header_bg = [srgb_to_linear(header[0]) * 0.5, srgb_to_linear(header[1]) * 0.5, srgb_to_linear(header[2]) * 0.5, 1.0]
                        p.overlay_header_background = header_bg
                        p.overlay_footer_background = header_bg

            # Toggle on: ThemeView3D.object_active
            if object_active := safe_getattr(view3d, 'object_active'):
                toggle_on_color = [srgb_to_linear(object_active[0]), srgb_to_linear(object_active[1]), srgb_to_linear(object_active[2]), 1.0]
                p.overlay_color_toggle_on = toggle_on_color
                # Group color: same as toggle on
                p.overlay_color_group = toggle_on_color

            # Toggle off: same as separator color
            if separator_color:
                p.overlay_color_toggle_off = separator_color
            
            # Counter color: same as label color
            if label_color:
                p.overlay_color_counter = label_color

            self.report({'INFO'}, "Overlay colors extracted from Blender theme")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to extract theme: {e}")
            return {'CANCELLED'}


# Built-in theme presets
BUILTIN_THEMES = {
    "default": {
        "name": "Default",
        "description": "ChordSong default theme",
        "colors": {
            "chord": [0.65, 0.80, 1.00, 1.00],
            "label": [1.00, 1.00, 1.00, 1.00],
            "header": [1.00, 1.00, 1.00, 1.00],
            "icon": [0.80, 0.80, 0.80, 1.00],
            "group": [1.00, 1.00, 1.00, 1.00],  # Same as label/text
            "counter": [1.00, 1.00, 1.00, 1.00],  # Same as label
            "toggle_on": [0.65, 0.80, 1.00, 0.40],
            "toggle_off": [1.00, 1.00, 1.00, 0.20],  # Same as separator
            "recents_hotkey": [0.65, 0.80, 1.00, 1.00],
            "separator": [1.00, 1.00, 1.00, 0.20],
            "list_background": [0.0, 0.0, 0.0, 0.35],
            "header_background": [0.0, 0.0, 0.0, 0.35],
            "footer_background": [0.0, 0.0, 0.0, 0.35],
        }
    }
}


class CHORDSONG_OT_LoadThemePreset(bpy.types.Operator):
    """Load a built-in theme preset"""

    bl_idname = "chordsong.load_theme_preset"
    bl_label = "Load Theme Preset"
    bl_options = {'REGISTER', 'UNDO'}

    preset_name: StringProperty(
        name="Preset",
        description="Theme preset to load",
        default="default"
    )

    def execute(self, context):
        p = prefs(context)

        if self.preset_name not in BUILTIN_THEMES:
            self.report({'ERROR'}, f"Unknown preset: {self.preset_name}")
            return {'CANCELLED'}

        theme = BUILTIN_THEMES[self.preset_name]
        colors = theme["colors"]

        # Apply colors
        p.overlay_color_chord = colors["chord"]
        p.overlay_color_label = colors["label"]
        p.overlay_color_header = colors["header"]
        p.overlay_color_icon = colors["icon"]
        p.overlay_color_group = colors.get("group", colors["label"])  # Default to label if missing
        p.overlay_color_counter = colors.get("counter", colors["label"])  # Default to label if missing
        p.overlay_color_separator = colors.get("separator", [1.0, 1.0, 1.0, 0.20])  # Default separator
        p.overlay_color_toggle_on = colors["toggle_on"]
        p.overlay_color_toggle_off = colors["toggle_off"]
        p.overlay_color_recents_hotkey = colors["recents_hotkey"]
        p.overlay_list_background = colors["list_background"]
        p.overlay_header_background = colors["header_background"]
        p.overlay_footer_background = colors["footer_background"]

        self.report({'INFO'}, f"Loaded theme preset: {theme['name']}")
        return {'FINISHED'}


# Registration
classes = (
    CHORDSONG_OT_ExportOverlayTheme,
    CHORDSONG_OT_ImportOverlayTheme,
    CHORDSONG_OT_ExtractBlenderTheme,
    CHORDSONG_OT_LoadThemePreset,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
