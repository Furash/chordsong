"""
Drawing logic for individual mapping items.
"""

from ...core.engine import get_str_attr, split_chord

def _is_mapping_conflicted(m, all_mappings):
    """Check if a mapping conflicts with other mappings in real-time."""
    if not getattr(m, "enabled", True):
        return False
    
    chord_str = get_str_attr(m, "chord")
    if not chord_str:
        return False
    
    chord_tokens = tuple(split_chord(chord_str))
    if not chord_tokens:
        return False
    
    context = getattr(m, "context", "VIEW_3D")
    
    # Check against all other enabled mappings in the same context
    # Mappings with "ALL" context should be checked against all contexts
    for other_m in all_mappings:
        if not getattr(other_m, "enabled", True):
            continue
        
        if other_m == m:
            continue
        
        other_context = getattr(other_m, "context", "VIEW_3D")
        # Skip if contexts don't match (unless one is "ALL")
        if context != "ALL" and other_context != "ALL" and other_context != context:
            continue
        
        other_chord_str = get_str_attr(other_m, "chord")
        if not other_chord_str:
            continue
        
        other_tokens = tuple(split_chord(other_chord_str))
        if not other_tokens:
            continue
        
        # Check for exact duplicate
        if chord_tokens == other_tokens:
            return True
        
        # Check for prefix conflict: this chord is prefix of other
        if len(chord_tokens) < len(other_tokens) and other_tokens[:len(chord_tokens)] == chord_tokens:
            return True
        
        # Check for prefix conflict: other chord is prefix of this
        if len(other_tokens) < len(chord_tokens) and chord_tokens[:len(other_tokens)] == other_tokens:
            return True
    
    return False

def draw_mapping_item(prefs, m, idx, layout, all_mappings=None):
    """Draw a single mapping item box."""
    # Wrap each mapping in its own box for clear visual separation
    item_box = layout.box()
    
    # Main row with enabled, chord, label, and remove button
    r = item_box.row(align=True)
    r.prop(m, "enabled", text="")
    
    # Chord field - highlight if conflicted
    chord_cell = r.row(align=True)
    chord_cell.scale_x = 0.5
    # Use all mappings if provided, otherwise fall back to prefs.mappings
    mappings_to_check = all_mappings if all_mappings is not None else prefs.mappings
    is_conflicted = _is_mapping_conflicted(m, mappings_to_check)
    # Always set alert state explicitly (don't rely on previous state)
    chord_cell.alert = is_conflicted
    chord_cell.prop(m, "chord", text="")
    
    r.separator()
    r.scale_x = 1.5
    r.prop(m, "label", text="")
    r.separator()

    # Group selection with searchable dropdown (now supports new group creation)
    r.prop(m, "group", text="", icon="FILE_FOLDER")

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
    
    # Context selector and mapping type selector - 2 rows
    # Row 1: First 3 context icons + 4 mapping type icons (continuing the same row)
    context_row1 = icon_col.row(align=True)
    context_row1.prop_enum(m, "context", "ALL", icon="WORLD", text="")
    context_row1.separator()
    context_row1.prop_enum(m, "context", "VIEW_3D", icon="OBJECT_DATAMODE", text="")
    context_row1.separator()
    context_row1.prop_enum(m, "context", "VIEW_3D_EDIT", icon="EDITMODE_HLT", text="")
    context_row1.separator()
    context_row1.separator()
    # Mapping type icons continue on the same row
    context_row1.prop_enum(m, "mapping_type", "OPERATOR", icon="SETTINGS", text="")
    context_row1.separator()
    context_row1.prop_enum(m, "mapping_type", "PYTHON_FILE", icon="FILE_SCRIPT", text="")
    context_row1.separator()
    context_row1.prop_enum(m, "mapping_type", "CONTEXT_TOGGLE", icon="CHECKBOX_HLT", text="")
    context_row1.separator()
    context_row1.prop_enum(m, "mapping_type", "CONTEXT_PROPERTY", icon="PROPERTIES", text="")
    
    # Row 2: Remaining 3 context icons
    context_row2 = icon_col.row(align=True)
    context_row2.prop_enum(m, "context", "GEOMETRY_NODE", icon="GEOMETRY_NODES", text="")
    context_row2.separator()
    context_row2.prop_enum(m, "context", "SHADER_EDITOR", icon="NODE_MATERIAL", text="")
    context_row2.separator()
    context_row2.prop_enum(m, "context", "IMAGE_EDITOR", icon="UV", text="")
    
    # Right side: Type-specific fields
    r2 = r2_split.column()

    if m.mapping_type == "PYTHON_FILE":
        _draw_python_mapping(r2, m, idx)
    elif m.mapping_type == "CONTEXT_TOGGLE":
        _draw_toggle_mapping(r2, m, idx)
    elif m.mapping_type == "CONTEXT_PROPERTY":
        _draw_property_mapping(r2, m, idx)
    else:
        _draw_operator_mapping(r2, m, idx)

def _draw_python_mapping(layout, m, idx):
    """Draw rows for a Python script mapping."""
    area = layout.box()
    
    gutter_f = 0.2
    master_f = 0.7
    ctx_f = 0.4
    
    def draw_row(label, ptr, prop, btn_op=None, btn_label=None, btn_icon=None, btn_idx=-1):
        row_block = area.column(align=True)
        master_split = row_block.split(factor=master_f, align=True)
        
        # Left side: Labeled input
        inputs = master_split.column(align=True)
        row = inputs.row(align=True)
        split = row.split(factor=gutter_f, align=True)
        split.alignment = 'RIGHT'
        split.label(text=label)
        split.prop(ptr, prop, text="")
        
        # Right side: Controls (aligned in the 'Invoke' slot for tidiness)
        controls = master_split.row(align=True)
        ctx = controls.split(factor=ctx_f, align=True)
        
        if btn_op:
            op = ctx.operator(btn_op, text=btn_label, icon=btn_icon)
            op.mapping_index = idx
            if btn_idx != -1:
                op.item_index = btn_idx
        else:
            ctx.label(text="")
            
        # Placeholder splits to maintain consistent alignment with Operator types
        rem = ctx.split(factor=0.5, align=True)
        rem.label(text="")
        rem.label(text="")
        
        row_block.separator(factor=0.4)

    # Main Script Row
    draw_row("Script:", m, "python_file", "chordsong.script_select", "Select", "FILE_SCRIPT")
    
    # Parameters Rows
    draw_row("Parameters:", m, "kwargs_json", "chordsong.subitem_add", "", "ADD")
    for i, p in enumerate(m.script_params):
        draw_row("", p, "value", "chordsong.subitem_remove", "", "TRASH", i)


def _draw_toggle_mapping(layout, m, idx):
    """Draw rows for a context toggle mapping."""
    area = layout.box()
    
    def draw_row(ptr, prop, is_primary, sub_idx=-1):
        op_block = area.column(align=True)
        master_split = op_block.split(factor=0.7, align=True)
        
        inputs_col = master_split.column(align=True)
        gutter_f = 0.2
        
        row = inputs_col.row(align=True)
        split = row.split(factor=gutter_f, align=True)
        split.alignment = 'RIGHT'
        split.label(text="Property:")
        split.prop(ptr, prop, text="")
        
        # Right side
        controls_row = master_split.row(align=True)
        ctx_split = controls_row.split(factor=0.4, align=True)
        if is_primary:
            ctx_split.prop(m, "sync_toggles", text="", icon='LINKED' if m.sync_toggles else 'UNLINKED', toggle=True)
        else:
            ctx_split.label(text="")
            
        btns_split = ctx_split.split(factor=0.5, align=True)
        if is_primary:
            op = btns_split.operator("chordsong.subitem_add", text="Add", icon="ADD")
            op.mapping_index = idx
        else:
            op = btns_split.operator("chordsong.subitem_remove", text="Del", icon="TRASH")
            op.mapping_index = idx
            op.item_index = sub_idx
        
        btns_split.label(text="") # Placeholder for 'Convert'
        
        op_block.separator(factor=0.4)

    draw_row(m, "context_path", True)
    for i, item in enumerate(m.sub_items):
        draw_row(item, "path", False, i)



def _draw_property_mapping(layout, m, idx):
    """Draw rows for a context property mapping."""
    area = layout.box()
    
    def draw_row(path_ptr, path_prop, val_ptr, val_prop, is_primary, sub_idx=-1):
        op_block = area.column(align=True)
        master_split = op_block.split(factor=0.7, align=True)
        
        inputs_col = master_split.column(align=True)
        gutter_f = 0.2
        
        # Path
        row1 = inputs_col.row(align=True)
        split1 = row1.split(factor=gutter_f, align=True)
        split1.alignment = 'RIGHT'
        split1.label(text="Property:")
        split1.prop(path_ptr, path_prop, text="")
        
        # Value
        row2 = inputs_col.row(align=True)
        split2 = row2.split(factor=gutter_f, align=True)
        split2.alignment = 'RIGHT'
        split2.label(text="Value:")
        split2.prop(val_ptr, val_prop, text="")
        
        # Right side
        controls_row = master_split.row(align=True)
        ctx_split = controls_row.split(factor=0.4, align=True)
        ctx_split.label(text="") # Placeholder
        
        btns_split = ctx_split.split(factor=0.5, align=True)
        if is_primary:
            op = btns_split.operator("chordsong.subitem_add", text="Add", icon="ADD")
            op.mapping_index = idx
        else:
            op = btns_split.operator("chordsong.subitem_remove", text="Del", icon="TRASH")
            op.mapping_index = idx
            op.item_index = sub_idx
            
        conv = btns_split.operator("chordsong.property_mapping_convert", text="Convert")
        conv.index = idx
        conv.sub_index = sub_idx
        
        op_block.separator(factor=0.4)

    draw_row(m, "context_path", m, "property_value", True)
    for i, item in enumerate(m.sub_items):
        draw_row(item, "path", item, "value", False, i)



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
