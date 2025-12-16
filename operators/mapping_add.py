# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import StringProperty, EnumProperty  # type: ignore

from .common import prefs


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
        items=(
            ("VIEW_3D", "3D View", "3D View editor"),
            ("GEOMETRY_NODE", "Geometry Nodes", "Geometry Nodes editor"),
            ("SHADER_EDITOR", "Shader Editor", "Shader Editor"),
        ),
        default="VIEW_3D",
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

        # Autosave is handled by update callbacks, but adding a new item may not trigger them.
        from .common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}


