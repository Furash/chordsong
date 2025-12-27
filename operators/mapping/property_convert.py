# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs

class CHORDSONG_OT_Property_Mapping_Convert(bpy.types.Operator):
    bl_idname = "chordsong.property_mapping_convert"
    bl_label = "Convert Property String"
    bl_description = "Parse full property assignment (e.g. bpy.context.space_data.clip_end = 900) into path and value"
    bl_options = {"INTERNAL"}

    index: IntProperty(default=-1)
    sub_index: IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        idx = int(self.index)
        sub_idx = int(self.sub_index)

        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        m = p.mappings[idx]
        if m.mapping_type != "CONTEXT_PROPERTY":
            self.report({"WARNING"}, "Can only convert property mappings")
            return {"CANCELLED"}

        # Target object: either the mapping itself or a sub-item
        target = m
        if sub_idx >= 0:
            if sub_idx < len(m.sub_items):
                target = m.sub_items[sub_idx]
            else:
                self.report({"WARNING"}, "Invalid sub-item index")
                return {"CANCELLED"}

        # Check path for '='
        path_field = "context_path" if target == m else "path"
        val_field = "property_value" if target == m else "value"
        
        path_text = (getattr(target, path_field) or "").strip()
        if "=" in path_text:
            parts = path_text.split("=", 1)
            left = parts[0].strip()
            right = parts[1].strip()

            # Clean up left part (remove bpy.context. prefix)
            if left.startswith("bpy.context."):
                left = left[len("bpy.context."):]
            elif left.startswith("context."):
                left = left[len("context."):]

            setattr(target, path_field, left)
            setattr(target, val_field, right)

            if target == m:
                # Derive label and suggest chord ONLY for primary item
                prop_id = left.split(".")[-1]
                label = prop_id.replace("_", " ").title()
                m.label = label
                
                if not m.group:
                    m.group = "Property"

                try:
                    from ..context_menu.suggester import suggest_chord
                    m.chord = suggest_chord(m.group, label)
                except Exception:
                    pass
            
            self.report({"INFO"}, f"Converted: {left} = {right}")
            return {"FINISHED"}

        # Also check if it's just a property path without assignment, in case property_value has the value
        # But usually users paste the whole thing into the Path field.
        
        self.report({"WARNING"}, "No '=' found in Path field to split")
        return {"CANCELLED"}
