"""Group selection operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy
from bpy.props import IntProperty, EnumProperty

from .common import prefs


def _get_available_groups(_self, context):
    """Get list of available groups for selection."""
    p = prefs(context)
    items = [("", "(No Group)", "Clear group assignment")]

    for grp in p.groups:
        if grp.name:
            items.append((grp.name, grp.name, f"Assign to {grp.name}"))

    return items if len(items) > 1 else [("", "(No Groups)", "No groups available")]


class CHORDSONG_OT_group_select(bpy.types.Operator):
    """Select group from existing groups for a mapping."""

    bl_idname = "chordsong.group_select"
    bl_label = "Select Group"
    bl_description = "Select from existing groups"
    bl_options = {"INTERNAL"}

    mapping_index: IntProperty(
        name="Mapping Index",
        description="Index of the mapping to set group for",
        default=-1,
    )

    selected_group: EnumProperty(
        name="Group",
        description="Select a group",
        items=_get_available_groups,
    )

    def invoke(self, context, event):
        """Show popup with available groups."""
        p = prefs(context)

        if self.mapping_index < 0 or self.mapping_index >= len(p.mappings):
            self.report({"ERROR"}, "Invalid mapping index")
            return {"CANCELLED"}

        # Pre-select current group if it exists
        current_group = p.mappings[self.mapping_index].group
        if current_group:
            self.selected_group = current_group

        return context.window_manager.invoke_props_popup(self, event)

    def draw(self, _context):
        """Draw group selection UI."""
        layout = self.layout
        layout.prop(self, "selected_group", text="")

    def execute(self, context):
        """Assign selected group to mapping."""
        p = prefs(context)

        if self.mapping_index < 0 or self.mapping_index >= len(p.mappings):
            self.report({"ERROR"}, "Invalid mapping index")
            return {"CANCELLED"}

        p.mappings[self.mapping_index].group = self.selected_group

        return {"FINISHED"}
