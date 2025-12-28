import bpy
from ...ui.prefs import _on_mapping_changed

class CHORDSONG_OT_SubItem_Add(bpy.types.Operator):
    """Add a new sub-action to this mapping"""
    bl_idname = "chordsong.subitem_add"
    bl_label = "Add Sub-action"
    bl_options = {'REGISTER', 'UNDO'}
    
    mapping_index: bpy.props.IntProperty()
    
    def execute(self, context):
        prefs = context.preferences.addons["chordsong"].preferences
        if self.mapping_index < 0 or self.mapping_index >= len(prefs.mappings):
            return {'CANCELLED'}
            
        m = prefs.mappings[self.mapping_index]
        if m.mapping_type == "OPERATOR":
            m.sub_operators.add()
        else:
            m.sub_items.add()
        
        _on_mapping_changed(self, context)
        return {'FINISHED'}

class CHORDSONG_OT_SubItem_Remove(bpy.types.Operator):
    """Remove a sub-action from this mapping"""
    bl_idname = "chordsong.subitem_remove"
    bl_label = "Remove Sub-action"
    bl_options = {'REGISTER', 'UNDO'}
    
    mapping_index: bpy.props.IntProperty()
    item_index: bpy.props.IntProperty()
    
    def execute(self, context):
        prefs = context.preferences.addons["chordsong"].preferences
        if self.mapping_index < 0 or self.mapping_index >= len(prefs.mappings):
            return {'CANCELLED'}
            
        m = prefs.mappings[self.mapping_index]
        
        if m.mapping_type == "OPERATOR":
            if self.item_index < 0 or self.item_index >= len(m.sub_operators):
                return {'CANCELLED'}
            m.sub_operators.remove(self.item_index)
        else:
            if self.item_index < 0 or self.item_index >= len(m.sub_items):
                return {'CANCELLED'}
            m.sub_items.remove(self.item_index)
        
        _on_mapping_changed(self, context)
        return {'FINISHED'}
