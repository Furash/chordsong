"""Group add operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import StringProperty

from ..common import prefs

class CHORDSONG_OT_Group_Add(bpy.types.Operator):
    """Add a new group."""

    bl_idname = "chordsong.group_add"
    bl_label = "Add New Group"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    name: StringProperty(
        name="Group Name",
        description="Name for the new group",
        default="New Group",
    )

    def invoke(self, context, _event):
        """Show dialog to enter group name."""
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        """Add the new group."""
        p = prefs(context)

        name = self.name.strip()
        if not name:
            self.report({"WARNING"}, "Group name cannot be empty")
            return {"CANCELLED"}

        for grp in p.groups:
            if grp.name == name:
                self.report({"WARNING"}, f"Group {name} already exists")
                return {"CANCELLED"}

        grp = p.groups.add()
        grp.name = name

        # Immediately sync and sort (Unreal-style) - delayed for stability
        p.sync_groups_delayed()

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        self.report({"INFO"}, f"Added group {name}")
        return {"FINISHED"}
