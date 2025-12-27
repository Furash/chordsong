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
        item = m.sub_items.add()
        
        # If this is the first sub-item being added, maybe we want to move the main path into it?
        # For now, let's just keep them separate or the user can manage.
        
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
        if self.item_index < 0 or self.item_index >= len(m.sub_items):
            return {'CANCELLED'}
            
        m.sub_items.remove(self.item_index)
        
        _on_mapping_changed(self, context)
        return {'FINISHED'}
