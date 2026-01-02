"""Group rename operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import IntProperty, StringProperty

from ..common import prefs

class CHORDSONG_OT_Group_Rename(bpy.types.Operator):
    """Rename a group and update all mappings using it."""

    bl_idname = "chordsong.group_rename"
    bl_label = "Rename Group"
    bl_options = {"INTERNAL"}

    index: IntProperty(
        name="Group Index",
        description="Index of the group to rename",
        default=-1,
        options={'HIDDEN'},
    )

    new_name: StringProperty(
        name="New Name",
        description="New name for the group",
        default="",
    )

    def invoke(self, context, _event):
        """Show dialog with current group name."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        self.new_name = p.groups[self.index].name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        """Rename group and update all mappings."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        old_name = p.groups[self.index].name
        new_name = self.new_name.strip()

        if not new_name:
            self.report({"WARNING"}, "Group name cannot be empty")
            return {"CANCELLED"}

        if new_name == old_name:
            return {"FINISHED"}

        for idx, grp in enumerate(p.groups):
            if idx != self.index and grp.name == new_name:
                self.report({"WARNING"}, f"Group {new_name} already exists")
                return {"CANCELLED"}

        count = 0
        for m in p.mappings:
            if m.group == old_name:
                m.group = new_name
                count += 1

        p.groups[self.index].name = new_name

        try:
            from ...core.autosave import schedule_autosave
            schedule_autosave(p, delay_s=5.0)
        except Exception:
            pass

        self.report({"INFO"}, f"Renamed group {old_name} to {new_name} ({count} mappings updated)")
        return {"FINISHED"}
