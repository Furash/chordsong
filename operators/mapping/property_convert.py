# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs
from ...utils.context_path import normalize_bpy_data_path

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
        if m.mapping_type not in ("CONTEXT_PROPERTY", "CONTEXT_TOGGLE"):
            self.report({"WARNING"}, "Can only convert property or toggle mappings")
            return {"CANCELLED"}
        
        is_toggle = m.mapping_type == "CONTEXT_TOGGLE"

        # Target object: either the mapping itself or a sub-item
        target = m
        if sub_idx >= 0:
            if sub_idx < len(m.sub_items):
                target = m.sub_items[sub_idx]
            else:
                self.report({"WARNING"}, "Invalid sub-item index")
                return {"CANCELLED"}

        # Get path field
        path_field = "context_path" if target == m else "path"
        path_text = (getattr(target, path_field) or "").strip()
        
        if not path_text:
            self.report({"WARNING"}, "No path to convert")
            return {"CANCELLED"}
        
        # Clean up path (remove bpy.context. or bpy.data. prefix and handle assignment)
        cleaned_path = path_text
        if cleaned_path.startswith("bpy.context."):
            cleaned_path = cleaned_path[len("bpy.context."):]
        elif cleaned_path.startswith("context."):
            cleaned_path = cleaned_path[len("context."):]
        elif cleaned_path.startswith("bpy.data."):
            # Use shared normalization utility function
            cleaned_path = normalize_bpy_data_path(cleaned_path)
        
        cleaned_path = cleaned_path.strip()
        
        # For properties, split on '=' to get path and value
        # For toggles, if '=' is present, take only the left side
        if "=" in cleaned_path:
            parts = cleaned_path.split("=", 1)
            cleaned_path = parts[0].strip()
            value_part = parts[1].strip() if not is_toggle else None
        else:
            value_part = None
        
        # Set the cleaned path
        setattr(target, path_field, cleaned_path)
        
        # For properties, also set the value field
        if not is_toggle:
            val_field = "property_value" if target == m else "value"
            if value_part is not None:
                setattr(target, val_field, value_part)
            else:
                self.report({"WARNING"}, "No '=' found in Path field to split")
                return {"CANCELLED"}
        
        # Derive label and suggest chord for primary item only
        if target == m:
            prop_id = cleaned_path.split(".")[-1]
            label = prop_id.replace("_", " ").title()
            m.label = label
            
            if not m.group:
                m.group = "Toggle" if is_toggle else "Property"
            
            try:
                from ..context_menu.suggester import suggest_chord
                m.chord = suggest_chord(m.group, label)
            except Exception:
                pass
        
        # Report success
        if is_toggle:
            self.report({"INFO"}, f"Converted: {cleaned_path}")
        else:
            self.report({"INFO"}, f"Converted: {cleaned_path} = {value_part}")
        
        return {"FINISHED"}
