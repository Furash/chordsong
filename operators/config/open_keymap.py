# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore


class CHORDSONG_OT_Open_Keymap(bpy.types.Operator):
    bl_idname = "chordsong.open_keymap"
    bl_label = "Open Keymap Preferences"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        try:
            # Switch the Preferences editor to the Keymap section if possible.
            context.preferences.active_section = "KEYMAP"
            self.report({"INFO"}, "Open Preferences → Keymap → Add-ons → Chord Song")
            return {"FINISHED"}
        except Exception:
            self.report({"INFO"}, "Open Preferences → Keymap → Add-ons → Chord Song")
            return {"FINISHED"}


