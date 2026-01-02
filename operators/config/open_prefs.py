# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

class CHORDSONG_OT_Open_Prefs(bpy.types.Operator):
    bl_idname = "chordsong.open_prefs"
    bl_label = "Open Add-on Preferences"
    bl_options = {"INTERNAL", "UNDO"}

    addon: bpy.props.StringProperty(
        name="Add-on Name",
        description="Module name of the addon (e.g. 'chordsong', 'InteractionOps')",
        default=""
    )

    def execute(self, context: bpy.types.Context):
        try:
            # Use provided name or fall back to current extension package
            target = self.addon
            if not target:
                # Extension format: bl_ext.{repo}.{addon_id}.{submodule...}
                # We need the first 3 parts: bl_ext.repo.addon_id
                parts = __package__.split(".")
                target = ".".join(parts[:3])

            # Open preferences and show the specific addon
            bpy.ops.preferences.addon_show(module=target)

            return {"FINISHED"}
        except Exception as ex:
            self.report({"WARNING"}, f"Failed to open preferences for '{self.addon or 'current addon'}': {ex}")
            return {"CANCELLED"}
