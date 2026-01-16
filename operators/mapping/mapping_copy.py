"""Copy chord mappings to clipboard."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy  # type: ignore

from ...core.chord_serialization import serialize_to_json_string
from ..common import prefs


class CHORDSONG_OT_Mapping_Copy(bpy.types.Operator):
    """Copy selected chord mappings to clipboard as JSON snippet."""

    bl_idname = "chordsong.mapping_copy"
    bl_label = "Copy Chords"
    bl_description = "Copy selected chord mappings to clipboard"

    def execute(self, context: bpy.types.Context):
        """Toggle selection mode or copy selected mappings."""
        p = prefs(context)

        # If not in selection mode, enable it
        if not p.selection_mode:
            p.selection_mode = True
            self.report({"INFO"}, "Selection mode enabled. Select chords and click 'Selecting...' to copy")
            return {"FINISHED"}

        # If in selection mode, perform the copy
        # Collect selected mapping indices
        selected_indices = []
        for idx, m in enumerate(p.mappings):
            if getattr(m, "selected", False):
                selected_indices.append(idx)

        # Always clear selections and exit selection mode, even if nothing was selected
        result_status = {"FINISHED"}

        if not selected_indices:
            self.report({"WARNING"}, "No chord mappings selected")
            result_status = {"CANCELLED"}
        else:
            try:
                # Serialize selected mappings
                json_str = serialize_to_json_string(p.mappings, selected_indices)

                # Copy to clipboard
                context.window_manager.clipboard = json_str

                count = len(selected_indices)
                plural = "chord" if count == 1 else "chords"
                self.report({"INFO"}, f"Copied {count} {plural} to clipboard")

            except Exception as ex:
                self.report({"ERROR"}, f"Failed to copy chords: {ex}")
                result_status = {"CANCELLED"}

        # Always clear selections and exit selection mode
        for m in p.mappings:
            if hasattr(m, "selected"):
                m.selected = False
        p.selection_mode = False

        return result_status


class CHORDSONG_OT_Mapping_Copy_Single(bpy.types.Operator):
    """Copy a single chord mapping to clipboard."""

    bl_idname = "chordsong.mapping_copy_single"
    bl_label = "Copy Chord"
    bl_description = "Copy this chord mapping to clipboard"
    bl_options = {"INTERNAL"}

    index: bpy.props.IntProperty()

    def execute(self, context: bpy.types.Context):
        """Copy single mapping to clipboard."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.mappings):
            self.report({"ERROR"}, "Invalid mapping index")
            return {"CANCELLED"}

        try:
            # Serialize single mapping
            json_str = serialize_to_json_string(p.mappings, [self.index])

            # Copy to clipboard
            context.window_manager.clipboard = json_str

            m = p.mappings[self.index]
            chord = getattr(m, "chord", "")
            self.report({"INFO"}, f"Copied chord '{chord}' to clipboard")
            return {"FINISHED"}

        except Exception as ex:
            self.report({"ERROR"}, f"Failed to copy chord: {ex}")
            return {"CANCELLED"}
