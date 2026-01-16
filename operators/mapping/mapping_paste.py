"""Paste chord mappings from clipboard."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy  # type: ignore

from ...core.chord_serialization import deserialize_from_json_string
from ...core.config_io import _add_mapping_from_dict
from ..common import prefs


class CHORDSONG_OT_Mapping_Paste(bpy.types.Operator):
    """Paste chord mappings from clipboard."""

    bl_idname = "chordsong.mapping_paste"
    bl_label = "Paste Chords"
    bl_description = "Paste chord mappings from clipboard"

    def execute(self, context: bpy.types.Context):
        """Paste mappings from clipboard."""
        p = prefs(context)
        
        # Get clipboard content
        clipboard_text = context.window_manager.clipboard
        if not clipboard_text or not clipboard_text.strip():
            self.report({"WARNING"}, "Clipboard is empty")
            return {"CANCELLED"}
        
        try:
            # Deserialize chord snippets
            chord_dicts, warnings = deserialize_from_json_string(clipboard_text)
            
            if not chord_dicts:
                self.report({"WARNING"}, "No valid chords found in clipboard")
                return {"CANCELLED"}
            
            # Add each chord as a new mapping (order_index will be normalized after)
            for chord_dict in chord_dicts:
                _add_mapping_from_dict(p, chord_dict, 0)
            
            # Normalize all order indices to match array positions (0, 1, 2, ...)
            # This ensures no gaps and makes move operations work correctly
            for idx, m in enumerate(p.mappings):
                m.order_index = idx
            
            # Clear overlay cache so new mappings appear
            from ...ui.overlay import clear_overlay_cache
            clear_overlay_cache()
            
            # Report results
            count = len(chord_dicts)
            plural = "chord" if count == 1 else "chords"
            message = f"Pasted {count} {plural}"
            
            if warnings:
                message += f" (with {len(warnings)} warning{'s' if len(warnings) > 1 else ''})"
                for warning in warnings[:3]:  # Show first 3 warnings
                    self.report({"WARNING"}, warning)
            
            self.report({"INFO"}, message)
            
            # Run conflict checker automatically
            bpy.ops.chordsong.check_conflicts()
            
            return {"FINISHED"}
        
        except ValueError as ex:
            self.report({"ERROR"}, f"Invalid clipboard format: {ex}")
            return {"CANCELLED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to paste chords: {ex}")
            return {"CANCELLED"}
