# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from ...utils.addon_package import addon_root_package

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
            addon_id = None
            
            if not target:
                # For both extensions & legacy add-ons, use the root package.
                target = addon_root_package(__package__) or "chordsong"
                addon_id = target.split(".")[-1]
            else:
                # If user provided a name, check if it's just the addon ID or full path
                if not target.startswith("bl_ext."):
                    addon_id = target  # Store for searching if not found
                else:
                    addon_id = target.split(".")[-1] if "." in target else target

            # Verify the addon exists in preferences before trying to show it
            if target not in context.preferences.addons:
                # Search for the addon ID across all extension repositories
                # Look for pattern: bl_ext.*.{addon_id}
                found_target = None
                for addon_name in context.preferences.addons.keys():
                    if addon_name.startswith("bl_ext.") and addon_name.endswith(f".{addon_id}"):
                        # Check if it matches the pattern bl_ext.{repo}.{addon_id}
                        parts = addon_name.split(".")
                        if len(parts) == 3 and parts[2] == addon_id:
                            found_target = addon_name
                            break
                
                if found_target:
                    target = found_target
                else:
                    self.report({"ERROR"}, f"Addon '{self.addon or addon_id or 'current addon'}' not found in preferences")
                    return {"CANCELLED"}

            # Open preferences window and show the specific addon
            # For extensions, addon_show requires the full module path (bl_ext.repo.addon_id)
            bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
            bpy.ops.preferences.addon_show(module=target)

            return {"FINISHED"}
        except Exception as ex:
            self.report({"WARNING"}, f"Failed to open preferences for '{self.addon or target or 'current addon'}': {ex}")
            return {"CANCELLED"}
