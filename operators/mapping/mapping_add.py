# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import StringProperty, EnumProperty  # type: ignore

from ..common import prefs
from ...core.contexts import DEFAULT_CONTEXT, enum_items as _context_enum_items

# "Global" (ALL) included so the sidebar's Global tab can add global chords.
_CONTEXT_ENUM_ITEMS = _context_enum_items(include_all=True, icons=False)

class CHORDSONG_OT_Mapping_Add(bpy.types.Operator):
    bl_idname = "chordsong.mapping_add"
    bl_label = "Add New Chord"
    bl_options = {"INTERNAL"}

    group: StringProperty(
        name="Group",
        description="Group to assign to the new chord",
        default="",
    )

    context: EnumProperty(
        name="Context",
        description="Editor context for the new chord",
        items=_CONTEXT_ENUM_ITEMS,
        default=DEFAULT_CONTEXT,
    )

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        m = p.mappings.add()
        m.enabled = True
        m.chord = ""
        m.label = "New Chord"
        m.group = self.group if self.group != "Ungrouped" else ""
        m.context = self.context
        m.operator = ""
        m.call_context = "EXEC_DEFAULT"
        m.kwargs_json = ""

        # Move the new item to the top of the list
        last_index = len(p.mappings) - 1
        if last_index > 0:
            p.mappings.move(last_index, 0)
        
        # Update order indices to match new positions
        for idx, mapping in enumerate(p.mappings):
            mapping.order_index = idx

        # Autosave is handled by update callbacks, but adding a new item may not trigger them.
        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}
