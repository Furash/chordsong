"""Group remove operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import EnumProperty, IntProperty

from ..common import prefs

def _get_target_groups(self, context):
    """Get list of target groups for reassignment."""
    try:
        p = prefs(context)
        # All items must have the same tuple length (5-tuples with icon and number)
        items = [
            ("__CLEAR__", "None (Clear Group)", "Moves mappings to Ungrouped", "X", 0),
            ("__DELETE__", "Delete Mappings", "Permanently delete all mappings in this group", "TRASH", 1),
        ]

        # Safely get the index to exclude
        exclude_index = getattr(self, "index", -1)
        
        # Add all other groups (must also be 5-tuples)
        if hasattr(p, "groups") and p.groups:
            item_num = 2  # Start after the two special options
            for idx, grp in enumerate(p.groups):
                if idx != exclude_index and grp.name and grp.name.strip():
                    items.append((grp.name, grp.name, f"Reassign to {grp.name}", "FOLDER", item_num))
                    item_num += 1
    except Exception:
        # Fallback to just the basic options
        items = [
            ("__CLEAR__", "None (Clear Group)", "Moves mappings to Ungrouped", "X", 0),
            ("__DELETE__", "Delete Mappings", "Permanently delete all mappings in this group", "TRASH", 1)
        ]

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
            # Ensure target_group is initialized with a valid value
            # Get the items first to ensure they're available
            items = _get_target_groups(self, context)
            if items and items[0][0] == "__CLEAR__":
                self.target_group = "__CLEAR__"
            return context.window_manager.invoke_props_dialog(self)
        # For empty groups, execute directly with default clear action
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
        """Remove group and reassign/delete mappings."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        group_name = p.groups[self.index].name
        # Use getattr with default in case property wasn't initialized
        target = getattr(self, "target_group", "__CLEAR__")

        count = 0
        if target == "__DELETE__":
            # Remove mappings belonging to this group
            to_remove = []
            for i, m in enumerate(p.mappings):
                if m.group == group_name:
                    to_remove.append(i)
            
            # Remove from last to first to preserve indices
            for i in reversed(to_remove):
                p.mappings.remove(i)
                count += 1
        elif target == "__CLEAR__":
            # Clear group assignment (make mappings Ungrouped)
            for m in p.mappings:
                if m.group == group_name:
                    m.group = ""
                    count += 1
        else:
            # Reassign to another group
            for m in p.mappings:
                if m.group == group_name:
                    m.group = target
                    count += 1

        p.groups.remove(self.index)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        if target == "__DELETE__":
            msg = f"Removed group {group_name} and deleted {count} mappings"
        elif target == "__CLEAR__":
            msg = f"Removed group {group_name} and cleared group from {count} mappings"
        else:
            msg = f"Removed group {group_name} and reassigned {count} mappings to {target}"

        self.report({"INFO"}, msg)
        return {"FINISHED"}
