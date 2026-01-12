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
                "toggle_on": list(p.overlay_color_toggle_on),
                "toggle_off": list(p.overlay_color_toggle_off),
                "recents_hotkey": list(p.overlay_color_recents_hotkey),
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
            if "toggle_on" in colors:
                p.overlay_color_toggle_on = colors["toggle_on"]
            if "toggle_off" in colors:
                p.overlay_color_toggle_off = colors["toggle_off"]
            if "recents_hotkey" in colors:
                p.overlay_color_recents_hotkey = colors["recents_hotkey"]
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
    bl_label = "Extract from Blender Theme"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        p = prefs(context)
        theme = context.preferences.themes[0]
        
        try:
            # Extract colors from current Blender theme
            ui = theme.user_interface
            view3d = theme.view_3d
            
            # Use theme colors for overlay
            # Chord color: Use highlight color
            if hasattr(ui, 'wcol_state'):
                p.overlay_color_chord = list(ui.wcol_state.inner_sel) + [1.0]
            
            # Label color: Use text color
            if hasattr(ui, 'wcol_regular'):
                p.overlay_color_label = list(ui.wcol_regular.text) + [1.0]
            
            # Header color: Use header text
            if hasattr(ui, 'wcol_menu'):
                p.overlay_color_header = list(ui.wcol_menu.text) + [1.0]
            
            # Icon color: Use icon color from theme
            if hasattr(ui, 'icon_alpha'):
                icon_base = list(ui.wcol_regular.text)
                p.overlay_color_icon = icon_base + [ui.icon_alpha]
            
            # Toggle colors: Use theme highlight
            if hasattr(ui, 'wcol_toggle'):
                p.overlay_color_toggle_on = list(ui.wcol_toggle.inner_sel) + [0.6]
                p.overlay_color_toggle_off = list(ui.wcol_toggle.inner) + [0.3]
            
            # Backgrounds: Use panel colors
            if hasattr(ui, 'wcol_regular'):
                bg_col = list(ui.wcol_regular.inner)
                p.overlay_list_background = bg_col + [0.7]
                p.overlay_header_background = bg_col + [0.7]
                p.overlay_footer_background = bg_col + [0.7]
            
            # Recents hotkey: Same as chord color
            p.overlay_color_recents_hotkey = list(p.overlay_color_chord)
            
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
            "icon": [0.80, 0.80, 0.80, 0.70],
            "toggle_on": [0.65, 0.80, 1.00, 0.40],
            "toggle_off": [1.00, 1.00, 1.00, 0.20],
            "recents_hotkey": [0.65, 0.80, 1.00, 1.00],
            "list_background": [0.0, 0.0, 0.0, 0.35],
            "header_background": [0.0, 0.0, 0.0, 0.35],
            "footer_background": [0.0, 0.0, 0.0, 0.35],
        }
    },
    "dark": {
        "name": "Dark",
        "description": "Dark theme with subtle accents",
        "colors": {
            "chord": [0.4, 0.6, 0.9, 1.00],
            "label": [0.9, 0.9, 0.9, 1.00],
            "header": [0.9, 0.9, 0.9, 1.00],
            "icon": [0.6, 0.6, 0.6, 0.70],
            "toggle_on": [0.4, 0.6, 0.9, 0.50],
            "toggle_off": [0.7, 0.7, 0.7, 0.25],
            "recents_hotkey": [0.4, 0.6, 0.9, 1.00],
            "list_background": [0.1, 0.1, 0.1, 0.50],
            "header_background": [0.05, 0.05, 0.05, 0.50],
            "footer_background": [0.05, 0.05, 0.05, 0.50],
        }
    },
    "light": {
        "name": "Light",
        "description": "Light theme for bright displays",
        "colors": {
            "chord": [0.2, 0.4, 0.8, 1.00],
            "label": [0.1, 0.1, 0.1, 1.00],
            "header": [0.1, 0.1, 0.1, 1.00],
            "icon": [0.3, 0.3, 0.3, 0.70],
            "toggle_on": [0.2, 0.4, 0.8, 0.50],
            "toggle_off": [0.4, 0.4, 0.4, 0.30],
            "recents_hotkey": [0.2, 0.4, 0.8, 1.00],
            "list_background": [0.95, 0.95, 0.95, 0.70],
            "header_background": [0.9, 0.9, 0.9, 0.70],
            "footer_background": [0.9, 0.9, 0.9, 0.70],
        }
    },
    "neon": {
        "name": "Neon",
        "description": "Vibrant neon colors",
        "colors": {
            "chord": [0.0, 1.0, 0.8, 1.00],
            "label": [1.0, 0.3, 1.0, 1.00],
            "header": [1.0, 1.0, 0.0, 1.00],
            "icon": [0.0, 0.8, 1.0, 0.80],
            "toggle_on": [0.0, 1.0, 0.8, 0.60],
            "toggle_off": [0.5, 0.5, 0.5, 0.30],
            "recents_hotkey": [1.0, 0.3, 1.0, 1.00],
            "list_background": [0.0, 0.0, 0.0, 0.60],
            "header_background": [0.0, 0.0, 0.0, 0.60],
            "footer_background": [0.0, 0.0, 0.0, 0.60],
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
