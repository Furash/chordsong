# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore


class CHORDSONG_OT_open_prefs(bpy.types.Operator):
    bl_idname = "chordsong.open_prefs"
    bl_label = "Open Chord Song Preferences"
    bl_options = {"INTERNAL", "UNDO"}

    def execute(self, context: bpy.types.Context):
        try:
            # Get the addon package name
            addon_name = __package__.split(".")[0]
            
            # Open preferences and show this addon
            # This operator handles opening the preferences window if needed
            bpy.ops.preferences.addon_show(module=addon_name)
            
            return {"FINISHED"}
        except Exception as ex:
            self.report({"WARNING"}, f"Failed to open preferences: {ex}")
            return {"CANCELLED"}
