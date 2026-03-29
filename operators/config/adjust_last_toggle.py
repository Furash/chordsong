"""Operator to toggle the 'adjust_last' flag exclusively within an operator chain."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

import bpy  # type: ignore
from bpy.props import IntProperty, BoolProperty  # type: ignore

from ..common import prefs


class CHORDSONG_OT_AdjustLastToggle(bpy.types.Operator):
    """Toggle which operator in the chain gets F9 Adjust Last Operation"""

    bl_idname = "chordsong.adjust_last_toggle"
    bl_label = "Toggle Adjust Last"
    bl_options = set()

    mapping_index: IntProperty()
    sub_index: IntProperty(default=-1)  # -1 means primary operator
    is_primary: BoolProperty(default=True)

    def execute(self, context):
        p = prefs(context)
        if not p or self.mapping_index >= len(p.mappings):
            return {"CANCELLED"}

        m = p.mappings[self.mapping_index]

        # Determine which item was clicked
        if self.is_primary:
            target_prop = m
        else:
            if self.sub_index < 0 or self.sub_index >= len(m.sub_operators):
                return {"CANCELLED"}
            target_prop = m.sub_operators[self.sub_index]

        # Toggle: if already on, turn off; if off, turn on and disable all others
        new_value = not target_prop.adjust_last

        # Turn off all operators in the chain first
        m.adjust_last = False
        for sub in m.sub_operators:
            sub.adjust_last = False

        # Set the target if toggling on
        if new_value:
            target_prop.adjust_last = True

        return {"FINISHED"}
