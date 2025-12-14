# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from .common import prefs


class CHORDSONG_OT_mapping_add(bpy.types.Operator):
    bl_idname = "chordsong.mapping_add"
    bl_label = "Add New Chord"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        m = p.mappings.add()
        m.enabled = True
        m.chord = ""
        m.label = "New Chord"
        m.group = ""
        m.operator = ""
        m.call_context = "EXEC_DEFAULT"
        m.kwargs_json = ""

        # Autosave is handled by update callbacks, but adding a new item may not trigger them.
        from .common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}


