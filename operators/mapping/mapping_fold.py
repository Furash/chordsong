"""Chord fold/unfold operators."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,relative-beyond-top-level

import bpy  # type: ignore

from ..common import prefs

class CHORDSONG_OT_Mapping_Fold_All(bpy.types.Operator):
    bl_idname = "chordsong.mapping_fold_all"
    bl_label = "Collapse All Chords"
    bl_description = "Collapse all chord mappings"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        for m in p.mappings:
            m.expanded = False
        return {"FINISHED"}

class CHORDSONG_OT_Mapping_Unfold_All(bpy.types.Operator):
    bl_idname = "chordsong.mapping_unfold_all"
    bl_label = "Expand All Chords"
    bl_description = "Expand all chord mappings"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        for m in p.mappings:
            m.expanded = True
        return {"FINISHED"}
