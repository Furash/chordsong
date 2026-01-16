"""Clear operator cache operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,relative-beyond-top-level

import bpy

class CHORDSONG_OT_Clear_Operator_Cache(bpy.types.Operator):
    """Clear the operator cache to refresh the operator search list."""
    
    bl_idname = "chordsong.clear_operator_cache"
    bl_label = "Clear Operator Cache"
    bl_description = "Clear the cached operator list to refresh search results (useful after installing/enabling new addons)"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        """Clear the operator cache."""
        try:
            from ...ui.prefs import clear_operator_cache
            clear_operator_cache()
            self.report({"INFO"}, "Operator cache cleared")
            return {"FINISHED"}
        except Exception as e:
            self.report({"ERROR"}, f"Failed to clear cache: {e}")
            return {"CANCELLED"}
