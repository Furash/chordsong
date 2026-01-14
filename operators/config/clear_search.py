"""Clear search operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,relative-beyond-top-level

import bpy
from ..common import prefs

class CHORDSONG_OT_Clear_Search(bpy.types.Operator):
    bl_idname = "chordsong.clear_search"
    bl_label = "Clear Search"
    bl_description = "Clear the chord search filter"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        p.chord_search = ""
        return {"FINISHED"}
