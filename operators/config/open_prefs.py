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
            addon_id = None
            
            if not target:
                # Extension format: bl_ext.{repo}.{addon_id}.{submodule...}
                # We need the first 3 parts: bl_ext.repo.addon_id
                # e.g., bl_ext.vscode_development.chordsong -> bl_ext.vscode_development.chordsong
                # The middle part (repo) can be anything, we just take first 3 parts
                parts = __package__.split(".")
                if len(parts) >= 3:
                    # Take first 3 parts: bl_ext.{repo}.{addon_id}
                    target = ".".join(parts[:3])
                    addon_id = parts[2]  # Store the addon ID part (e.g., "chordsong")
                else:
                    # Fallback: use the full package name
                    target = __package__ if __package__ else "chordsong"
                    addon_id = parts[-1] if parts else "chordsong"
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
