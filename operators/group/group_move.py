"""Group move operators for reordering groups."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy
from bpy.props import IntProperty

from ..common import prefs


class CHORDSONG_OT_Group_Move_Up(bpy.types.Operator):
    """Move group up in the list."""

    bl_idname = "chordsong.group_move_up"
    bl_label = "Move Group Up"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    index: IntProperty(
        name="Index",
        description="Index of the group to move",
        default=-1,
    )

    def execute(self, context):
        """Move the group up."""
        p = prefs(context)

        idx = int(self.index)
        if idx < 0 or idx >= len(p.groups):
            self.report({"WARNING"}, "Invalid group index")
            return {"CANCELLED"}

        if idx == 0:
            # Already at the top
            return {"CANCELLED"}

        # Swap with previous group using move()
        p.groups.move(idx, idx - 1)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=3.0)

        return {"FINISHED"}


class CHORDSONG_OT_Group_Move_Down(bpy.types.Operator):
    """Move group down in the list."""

    bl_idname = "chordsong.group_move_down"
    bl_label = "Move Group Down"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    index: IntProperty(
        name="Index",
        description="Index of the group to move",
        default=-1,
    )

    def execute(self, context):
        """Move the group down."""
        p = prefs(context)

        idx = int(self.index)
        if idx < 0 or idx >= len(p.groups):
            self.report({"WARNING"}, "Invalid group index")
            return {"CANCELLED"}

        if idx >= len(p.groups) - 1:
            # Already at the bottom
            return {"CANCELLED"}

        # Swap with next group using move()
        p.groups.move(idx, idx + 1)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=3.0)

        return {"FINISHED"}
