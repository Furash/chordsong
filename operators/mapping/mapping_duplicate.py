# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs

class CHORDSONG_OT_Mapping_Duplicate(bpy.types.Operator):
    bl_idname = "chordsong.mapping_duplicate"
    bl_label = "Duplicate Chord"
    bl_options = {"INTERNAL"}

    index: IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        idx = int(self.index)
        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        # Get the source mapping
        source = p.mappings[idx]

        # Create new mapping
        new_m = p.mappings.add()

        # Copy all properties from source
        new_m.enabled = source.enabled
        new_m.chord = source.chord
        new_m.label = f"{source.label} (Copy)" if source.label else "New Chord"
        new_m.icon = source.icon
        new_m.group = source.group
        new_m.context = source.context
        new_m.mapping_type = source.mapping_type
        new_m.operator = source.operator
        new_m.python_file = source.python_file
        new_m.context_path = source.context_path
        new_m.call_context = source.call_context
        new_m.kwargs_json = source.kwargs_json
        new_m.property_value = source.property_value
        new_m.adjust_last = source.adjust_last
        new_m.sync_toggles = source.sync_toggles

        # Deep-copy sub-operator chain
        for src_sub in source.sub_operators:
            dst = new_m.sub_operators.add()
            dst.operator = src_sub.operator
            dst.call_context = src_sub.call_context
            dst.kwargs_json = src_sub.kwargs_json
            dst.adjust_last = src_sub.adjust_last

        # Deep-copy sub-items (toggles/properties)
        for src_sub in source.sub_items:
            dst = new_m.sub_items.add()
            dst.path = src_sub.path
            dst.value = src_sub.value

        # Deep-copy script parameters
        for src_param in source.script_params:
            dst = new_m.script_params.add()
            dst.value = src_param.value

        # Move the duplicated item right after the source
        new_index = len(p.mappings) - 1
        target_index = idx + 1
        if target_index < new_index:
            p.mappings.move(new_index, target_index)
        
        # Update order indices to match new positions
        for i, mapping in enumerate(p.mappings):
            mapping.order_index = i

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}
