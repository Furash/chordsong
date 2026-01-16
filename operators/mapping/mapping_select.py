"""Selection operators for chord mappings."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy  # type: ignore

from ..common import prefs


class CHORDSONG_OT_Mapping_Toggle_Select(bpy.types.Operator):
    """Toggle selection for a chord mapping."""

    bl_idname = "chordsong.mapping_toggle_select"
    bl_label = "Toggle Select"
    bl_description = "Toggle selection for this chord mapping"
    bl_options = {"INTERNAL"}

    index: bpy.props.IntProperty()

    def execute(self, context: bpy.types.Context):
        """Toggle mapping selection."""
        p = prefs(context)
        
        if self.index < 0 or self.index >= len(p.mappings):
            return {"CANCELLED"}
        
        m = p.mappings[self.index]
        current_state = getattr(m, "selected", False)
        m.selected = not current_state
        
        return {"FINISHED"}


class CHORDSONG_OT_Mapping_Deselect_All(bpy.types.Operator):
    """Deselect all chord mappings."""

    bl_idname = "chordsong.mapping_deselect_all"
    bl_label = "Deselect All"
    bl_description = "Deselect all chord mappings"

    def execute(self, context: bpy.types.Context):
        """Deselect all mappings."""
        p = prefs(context)
        
        count = 0
        for m in p.mappings:
            if getattr(m, "selected", False):
                m.selected = False
                count += 1
        
        if count > 0:
            plural = "chord" if count == 1 else "chords"
            self.report({"INFO"}, f"Deselected {count} {plural}")
        
        return {"FINISHED"}
