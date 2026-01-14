"""Group edit operator for editing group properties."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import IntProperty, StringProperty

from ..common import prefs

class CHORDSONG_OT_Group_Edit(bpy.types.Operator):
    """Edit group properties (name and icon)."""

    bl_idname = "chordsong.group_edit"
    bl_label = "Edit Group"
    bl_options = {"INTERNAL"}

    index: IntProperty(
        name="Group Index",
        description="Index of the group to edit",
        default=-1,
        options={'HIDDEN'},
    )

    new_name: StringProperty(
        name="Name",
        description="Group name",
        default="",
    )
    
    new_icon: StringProperty(
        name="Icon",
        description="Nerd Fonts emoji/icon for this group",
        default="",
    )
    
    _initial_icon: str = ""  # Store initial icon value to detect external updates

    def invoke(self, context, _event):
        """Show dialog with current group properties."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        self.new_name = p.groups[self.index].name
        self.new_icon = p.groups[self.index].icon
        self._initial_icon = p.groups[self.index].icon
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        """Draw the edit dialog."""
        layout = self.layout
        
        # Sync new_icon with group icon if it was updated externally (via icon_select)
        # Only sync if group icon changed from initial value and differs from current new_icon
        p = prefs(context)
        if self.index >= 0 and self.index < len(p.groups):
            current_group_icon = p.groups[self.index].icon
            # If group icon was updated externally (different from initial) and differs from new_icon, sync it
            if current_group_icon != self._initial_icon and current_group_icon != self.new_icon:
                self.new_icon = current_group_icon
        
        col = layout.column()
        col.prop(self, "new_name")
        
        row = col.row(align=True)
        row.prop(self, "new_icon", text="Icon")
        op = row.operator("chordsong.icon_select", text="", icon="THREE_DOTS")
        op.group_index = self.index
        op.target_prop = "new_icon"

    def execute(self, context):
        """Update group properties and mappings."""
        p = prefs(context)

        if self.index < 0 or self.index >= len(p.groups):
            self.report({"ERROR"}, "Invalid group index")
            return {"CANCELLED"}

        old_name = p.groups[self.index].name
        new_name = self.new_name.strip()

        if not new_name:
            self.report({"WARNING"}, "Group name cannot be empty")
            return {"CANCELLED"}

        if new_name != old_name:
            # Check for duplicate names
            for idx, grp in enumerate(p.groups):
                if idx != self.index and grp.name == new_name:
                    self.report({"WARNING"}, f"Group {new_name} already exists")
                    return {"CANCELLED"}

            # Update all mappings that use this group
            count = 0
            for m in p.mappings:
                if m.group == old_name:
                    m.group = new_name
                    count += 1

            p.groups[self.index].name = new_name
            
        # Update icon - always use what the user entered in the dialog
        p.groups[self.index].icon = self.new_icon

        try:
            from ...core.autosave import schedule_autosave
            schedule_autosave(p, delay_s=5.0)
        except Exception:
            pass

        self.report({"INFO"}, f"Updated group: {new_name}")
        return {"FINISHED"}
