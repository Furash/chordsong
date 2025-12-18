# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from ..common import prefs


class CHORDSONG_OT_Group_Fold_All(bpy.types.Operator):
    bl_idname = "chordsong.group_fold_all"
    bl_label = "Collapse All Groups"
    bl_description = "Collapse all group sections"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        p.ungrouped_expanded = False
        for grp in p.groups:
            grp.expanded = False
        return {"FINISHED"}


class CHORDSONG_OT_Group_Unfold_All(bpy.types.Operator):
    bl_idname = "chordsong.group_unfold_all"
    bl_label = "Expand All Groups"
    bl_description = "Expand all group sections"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        p.ungrouped_expanded = True
        for grp in p.groups:
            grp.expanded = True
        return {"FINISHED"}
