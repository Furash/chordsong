# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from .common import prefs


class CHORDSONG_OT_load_default(bpy.types.Operator):
    bl_idname = "chordsong.load_default"
    bl_label = "Load Default Chord Song Config"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        try:
            p._chordsong_suspend_autosave = True

            # Reset core prefs to their defaults (as defined in Property declarations).
            p.timeout_ms = 0

            p.overlay_enabled = True
            p.overlay_max_items = 14
            p.overlay_column_rows = 12
            p.overlay_font_size_header = 18
            p.overlay_font_size_chord = 16
            p.overlay_font_size_body = 14
            p.overlay_color_chord = (0.65, 0.80, 1.00, 1.00)
            p.overlay_color_label = (1.00, 1.00, 1.00, 1.00)
            p.overlay_color_header = (1.00, 1.00, 1.00, 1.00)
            p.overlay_position = "BOTTOM_LEFT"
            p.overlay_offset_x = 14
            p.overlay_offset_y = 14

            # Reset mappings to built-in defaults.
            p.mappings.clear()
            p.ensure_defaults()

            self.report({"INFO"}, "Loaded default config")
            return {"FINISHED"}
        finally:
            try:
                p._chordsong_suspend_autosave = False
            except Exception:
                pass



