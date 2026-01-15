# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import os

import bpy  # type: ignore

from ...core.config_io import apply_config, loads_json
from ...ui.prefs import default_config_path
from ..common import prefs

def _get_default_config_path():
    """Get the path to the default config file in the ui directory."""
    # Try to import ui module and get its path
    try:
        from ... import ui
        if hasattr(ui, "__file__") and ui.__file__:
            ui_dir = os.path.dirname(ui.__file__)
            return os.path.join(ui_dir, "default_mappings.json")
    except (ImportError, AttributeError):
        pass
    
    # Fallback: try relative to this file
    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(addon_dir, "ui", "default_mappings.json")

class CHORDSONG_OT_Load_Default(bpy.types.Operator):
    bl_idname = "chordsong.load_default"
    bl_label = "Load Default Chord Song Config"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        try:
            p._chordsong_suspend_autosave = True

            # Load default config from JSON file
            bundled_config_path = _get_default_config_path()
            if not os.path.exists(bundled_config_path):
                self.report({"ERROR"}, f"Default config file not found: {bundled_config_path}")
                return {"CANCELLED"}

            with open(bundled_config_path, "r", encoding="utf-8") as f:
                data = loads_json(f.read())

            # Apply the default config (mappings, groups, etc.)
            warnings = apply_config(p, data)
            for w in warnings[:5]:
                self.report({"WARNING"}, w)

            # Reset all UI settings to default values (after loading config)
            self._reset_prefs_to_defaults(p)

            # Match current Blender theme
            bpy.ops.chordsong.extract_blender_theme()

            # Set the config path to the default extension-specific directory
            default_path = default_config_path()
            if default_path:
                p.config_path = default_path

            self.report({"INFO"}, "Loaded default config")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to load default config: {ex}")
            return {"CANCELLED"}
        finally:
            p._chordsong_suspend_autosave = False
    
    def _reset_prefs_to_defaults(self, prefs_obj):
        """Reset all UI preference properties to their default values."""
        # Display Control Settings
        prefs_obj.overlay_hide_panels = True
        
        # Scripts Overlay Settings
        prefs_obj.scripts_overlay_max_items = 45
        prefs_obj.scripts_overlay_gap = 5.0
        prefs_obj.scripts_overlay_column_gap = 25.0
        prefs_obj.scripts_overlay_max_label_length = 0
        prefs_obj.scripts_overlay_column_rows = 9
        
        # Overlay Settings
        prefs_obj.overlay_enabled = True
        prefs_obj.overlay_fading_enabled = True
        prefs_obj.overlay_max_items = 50
        prefs_obj.overlay_column_rows = 8
        prefs_obj.overlay_show_header = True
        prefs_obj.overlay_show_footer = True
        
        # Typography
        prefs_obj.overlay_font_size_header = 14
        prefs_obj.overlay_font_size_chord = 18
        prefs_obj.overlay_font_size_body = 15
        prefs_obj.overlay_font_size_footer = 12
        prefs_obj.overlay_font_size_fading = 24
        prefs_obj.overlay_font_size_toggle = 23
        prefs_obj.overlay_toggle_offset_y = -4
        prefs_obj.overlay_font_size_separator = 15
        
        # Positioning
        prefs_obj.overlay_position = "BOTTOM_LEFT"
        prefs_obj.overlay_offset_x = 65
        prefs_obj.overlay_offset_y = -15
        
        # Layout
        prefs_obj.overlay_gap = 10
        prefs_obj.overlay_column_gap = 100
        prefs_obj.overlay_line_height = 1.5
        prefs_obj.overlay_max_label_length = 0
        
        # Footer
        prefs_obj.overlay_footer_gap = 50
        prefs_obj.overlay_footer_token_gap = 4
        prefs_obj.overlay_footer_label_gap = 8
        
        # Format
        prefs_obj.overlay_item_format = "DEFAULT"
        prefs_obj.overlay_format_folder = "C n s G L"
        prefs_obj.overlay_format_item = "C I S L T"
        prefs_obj.overlay_separator_a = "→"
        prefs_obj.overlay_separator_b = "::"
        
        # Colors (RGBA tuples)
        prefs_obj.overlay_color_chord = (0.65, 0.80, 1.00, 1.00)
        prefs_obj.overlay_color_label = (1.00, 1.00, 1.00, 1.00)
        prefs_obj.overlay_color_header = (1.00, 1.00, 1.00, 1.00)
        prefs_obj.overlay_color_icon = (0.80, 0.80, 0.80, 1.00)
        prefs_obj.overlay_color_toggle_on = (0.65, 0.80, 1.00, 0.40)
        prefs_obj.overlay_color_toggle_off = (1.00, 1.00, 1.00, 0.20)
        prefs_obj.overlay_color_recents_hotkey = (0.65, 0.80, 1.00, 1.00)
        prefs_obj.overlay_color_separator = (1.00, 1.00, 1.00, 0.20)
        prefs_obj.overlay_color_group = (0.90, 0.90, 0.50, 1.00)
        prefs_obj.overlay_color_counter = (0.80, 0.80, 0.80, 0.80)
        prefs_obj.overlay_list_background = (0.0, 0.0, 0.0, 0.35)
        prefs_obj.overlay_header_background = (0.0, 0.0, 0.0, 0.35)
        prefs_obj.overlay_footer_background = (0.0, 0.0, 0.0, 0.35)
        
        # Other UI settings
        prefs_obj.ungrouped_expanded = False
        prefs_obj.chord_search = ""
        
        if hasattr(prefs_obj, 'ensure_defaults'):
            prefs_obj.ensure_defaults()
