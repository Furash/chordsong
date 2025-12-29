"""
Drawing logic for individual mapping items.
"""

def draw_mapping_item(prefs, m, idx, layout):
    """Draw a single mapping item box."""
    # Wrap each mapping in its own box for clear visual separation
    item_box = layout.box()
    
    # Main row with enabled, chord, label, and remove button
    r = item_box.row(align=True)
    r.prop(m, "enabled", text="")
    r.scale_x = 0.5
    r.prop(m, "chord", text="")
    r.separator()
    r.scale_x = 1.5
    r.prop(m, "label", text="")
    r.separator()

    # Group selection with searchable dropdown
    r.prop_search(m, "group", prefs, "groups", icon="FILE_FOLDER", text="")

    r.separator()

    # Icon display and selection button (compact)
    icon_sub = r.row(align=True)
    icon_sub.scale_x = 0.75
    icon_sub.prop(m, "icon", text="Icon")
    icon_sub.separator()
    op = r.operator("chordsong.icon_select", text="", icon="DOWNARROW_HLT", emboss=False)
    op.mapping_index = idx
    op = r.operator("chordsong.mapping_duplicate", text="", icon="DUPLICATE", emboss=True)
    op.index = idx
    op = r.operator("chordsong.mapping_remove", text="", icon="X", emboss=True)
    op.index = idx

    # Second row with context and type selector and type-specific fields
    row2 = item_box.row(align=True)
    
    # Use a split to separate icons from the action area
    r2_split = row2.split(factor=0.21, align=True)
    
    # Left side: Icons
    icon_col = r2_split.column()
    icon_col.separator(factor=0.5)
    icon_row = icon_col.row(align=True)
    
    # Context selector (icon-only)
    icon_row.prop_enum(m, "context", "VIEW_3D", icon="OBJECT_DATAMODE", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "context", "VIEW_3D_EDIT", icon="EDITMODE_HLT", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "context", "GEOMETRY_NODE", icon="GEOMETRY_NODES", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "context", "SHADER_EDITOR", icon="NODE_MATERIAL", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "context", "IMAGE_EDITOR", icon="UV", text="")
    icon_row.separator()
    icon_row.separator()
    
    # Icon-only mapping type selector
    icon_row.prop_enum(m, "mapping_type", "OPERATOR", icon="SETTINGS", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "mapping_type", "PYTHON_FILE", icon="FILE_SCRIPT", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "mapping_type", "CONTEXT_TOGGLE", icon="CHECKBOX_HLT", text="")
    icon_row.separator()
    icon_row.prop_enum(m, "mapping_type", "CONTEXT_PROPERTY", icon="PROPERTIES", text="")
    
    # Right side: Type-specific fields
    r2 = r2_split.column()

    if m.mapping_type == "PYTHON_FILE":
        # For script, we don't need a box, but we need horizontal alignment
        script_row = r2.row(align=True)
        script_row.prop(m, "python_file", text="")
        script_row.separator()
        op = script_row.operator("chordsong.script_select", text="Select Script", icon="FILEBROWSER", emboss=True)
        op.mapping_index = idx
        
    elif m.mapping_type == "CONTEXT_TOGGLE":
        _draw_toggle_mapping(r2, m, idx)

    elif m.mapping_type == "CONTEXT_PROPERTY":
        _draw_property_mapping(r2, m, idx)
    else:
        _draw_operator_mapping(r2, m, idx)

def _draw_toggle_mapping(layout, m, idx):
    """Draw rows for a context toggle mapping."""
    def draw_toggle_row_fixed(layout, path_ptr, path_prop, is_primary, m, idx, sub_idx=-1):
        row = layout.row(align=True)
        p_split = row.split(factor=0.75, align=True)
        p_split.prop(path_ptr, path_prop, text="")
        
        b_split = p_split.split(factor=0.12, align=True)
        b_split.prop(m, "sync_toggles", text="", icon='LINKED' if m.sync_toggles else 'UNLINKED', toggle=True)

        if is_primary:
            op = b_split.operator("chordsong.subitem_add", text="Add Property", icon="ADD")
            op.mapping_index = idx
        else:
            rem = b_split.operator("chordsong.subitem_remove", text="Remove Property", icon="TRASH")
            rem.mapping_index = idx
            rem.item_index = sub_idx

    draw_toggle_row_fixed(layout, m, "context_path", True, m, idx)
    for i, item in enumerate(m.sub_items):
        draw_toggle_row_fixed(layout, item, "path", False, m, idx, i)

def _draw_property_mapping(layout, m, idx):
    """Draw rows for a context property mapping."""
    prop_area = layout.box()
    
    def draw_prop_row(layout, path_ptr, path_prop, val_ptr, val_prop, is_primary, sub_idx=-1):
        row = layout.row(align=True)
        path_split = row.split(factor=0.35, align=True)
        path_split.prop(path_ptr, path_prop, text="")
        
        val_split = path_split.split(factor=0.5, align=True)
        val_split.prop(val_ptr, val_prop, text="Value")
        
        btn_row = val_split.row(align=True)
        conv = btn_row.operator("chordsong.property_mapping_convert", text="Convert", icon="SOLO_ON")
        conv.index = idx
        conv.sub_index = sub_idx

        if is_primary:
            op_add = btn_row.operator("chordsong.subitem_add", text="Add", icon="ADD")
            op_add.mapping_index = idx
        else:
            rem = btn_row.operator("chordsong.subitem_remove", text="Remove", icon="TRASH")
            rem.mapping_index = idx
            rem.item_index = sub_idx
    
    draw_prop_row(prop_area, m, "context_path", m, "property_value", True)
    for i, item in enumerate(m.sub_items):
        draw_prop_row(prop_area, item, "path", item, "value", False, i)

def _draw_operator_mapping(layout, m, idx):
    """Draw rows for an operator mapping."""
    op_area = layout.box()
    
    def draw_op_row(layout, m_ptr, op_prop, ctx_prop, kwargs_prop, is_primary, sub_idx=-1):
        op_block = layout.column(align=True)
        master_split = op_block.split(factor=0.7, align=True)
        
        inputs_col = master_split.column(align=True)
        gutter_f = 0.2
        
        id_row = inputs_col.row(align=True)
        id_split = id_row.split(factor=gutter_f, align=True)
        id_split.alignment = 'RIGHT'
        id_split.label(text="Operator:") 
        id_split.prop(m_ptr, op_prop, text="")
        
        p_row = inputs_col.row(align=True)
        p_split = p_row.split(factor=gutter_f, align=True)
        p_split.alignment = 'RIGHT'
        p_split.label(text="Parameters:")
        p_split.prop(m_ptr, kwargs_prop, text="")
        
        controls_row = master_split.row(align=True)
        ctx_split = controls_row.split(factor=0.4, align=True)
        ctx_split.prop(m_ptr, ctx_prop, text="")
        
        btns_split = ctx_split.split(factor=0.5, align=True)
        if is_primary:
            op_add = btns_split.operator("chordsong.subitem_add", text="Add", icon="ADD")
            op_add.mapping_index = idx
        else:
            rem = btns_split.operator("chordsong.subitem_remove", text="Del", icon="TRASH")
            rem.mapping_index = idx
            rem.item_index = sub_idx
        
        conv = btns_split.operator("chordsong.mapping_convert", text="Convert")
        conv.index = idx
        conv.sub_index = sub_idx
        
        layout.separator(factor=0.4)

    draw_op_row(op_area, m, "operator", "call_context", "kwargs_json", True)
    for i, sub_op in enumerate(m.sub_operators):
        draw_op_row(op_area, sub_op, "operator", "call_context", "kwargs_json", False, i)
