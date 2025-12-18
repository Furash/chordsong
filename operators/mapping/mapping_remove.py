# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs

class CHORDSONG_OT_Mapping_Remove(bpy.types.Operator):
    bl_idname = "chordsong.mapping_remove"
    bl_label = "Remove Chord"
    bl_options = {"INTERNAL"}

    index: IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        idx = int(self.index)
        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        p.mappings.remove(idx)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}
