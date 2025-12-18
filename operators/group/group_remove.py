"""Group remove operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import EnumProperty, IntProperty

from ..common import prefs


def _get_target_groups(self, context):
    """Get list of target groups for reassignment."""
    p = prefs(context)
    items = [("", "None (Clear)", "Remove group from mappings")]

    for idx, grp in enumerate(p.groups):
        if idx != self.index:
            items.append((grp.name, grp.name, f"Reassign to {grp.name}"))

    return items


class CHORDSONG_OT_Group_Remove(bpy.types.Operator):
    """Remove a group and optionally reassign its mappings."""

    bl_idname = "chordsong.group_remove"
    bl_label = "Remove Group"
    bl_options = {"INTERNAL"}

    index: IntProperty(
        name="Group Index",
        description="Index of the group to remove",
        default=-1,
    )

    target_group: EnumProperty(
        name="Reassign To",
        description="Choose what to do with mappings in this group",
        items=_get_target_groups,
    )

    def invoke(self, context, _event):
        """Show dialog if group has mappings, otherwise execute directly."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        group_name = p.groups[self.index].name
        count = sum(1 for m in p.mappings if m.group == group_name)

        if count > 0:
            return context.window_manager.invoke_props_dialog(self)
        return self.execute(context)

    def draw(self, context):
        """Draw dialog for reassigning mappings."""
        layout = self.layout
        p = prefs(context)

        if 0 <= self.index < len(p.groups):
            group_name = p.groups[self.index].name
            count = sum(1 for m in p.mappings if m.group == group_name)

            layout.label(text=f"Remove group {group_name}?")
            layout.label(text=f"{count} mappings use this group")
            layout.separator()
            layout.prop(self, "target_group")

    def execute(self, context):
        """Remove group and reassign mappings."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        group_name = p.groups[self.index].name
        target = self.target_group.strip()

        count = 0
        for m in p.mappings:
            if m.group == group_name:
                m.group = target
                count += 1

        p.groups.remove(self.index)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        if target:
            msg = f"Removed group {group_name} and reassigned {count} mappings to {target}"
            self.report({"INFO"}, msg)
        else:
            msg = f"Removed group {group_name} and cleared {count} mappings"
            self.report({"INFO"}, msg)

        return {"FINISHED"}
