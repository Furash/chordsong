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

def _draw_dropdowns(layout, m, split_factor=0.35, left_padding=0.0, separator_factor=0.8, context_scale=0.3, type_scale=0.15):
    """Draw context and mapping type dropdown selectors.

    Args:
        layout: The layout to draw into
        m: The mapping object
        split_factor: Factor for left/right split (default 0.35)
        left_padding: Scale factor for left padding label (default 0.0)
        separator_factor: Vertical separator factor above dropdowns (default 0.8)
        context_scale: Scale factor for context dropdown (default 0.3)
        type_scale: Scale factor for type dropdown (default 0.15)

    Returns:
        The right column layout for type-specific fields
    """
    row = layout.row(align=True)
    split = row.split(factor=split_factor, align=True)

    # Left side: Dropdown selectors in a single row
    dropdown_col = split.column(align=True)
    dropdown_col.separator(factor=separator_factor)
    dropdown_row = dropdown_col.row(align=True)

    # Optional left padding
    if left_padding > 0:
        dropdown_row.scale_x = left_padding
        dropdown_row.label(text="")

    # Context dropdown selector
    dropdown_row.scale_x = context_scale
    dropdown_row.prop(m, "context", text="")

    dropdown_row.separator()

    # Mapping type dropdown selector
    dropdown_row.scale_x = type_scale
    dropdown_row.prop(m, "mapping_type", text="")

    # Right side: Type-specific fields
    return split.column()

def draw_mapping_item(prefs, m, idx, layout, all_mappings=None, search_query=""):
    """Draw a single mapping item box."""
    # Get expanded state (default to True if not set)
    is_expanded = getattr(m, "expanded", True)

    # Auto-expand items when search is active
    if search_query:
        is_expanded = True
    
    # Use compact column for collapsed items, box for expanded
    if not is_expanded:
        item_box = layout.column(align=True)
    else:
        item_box = layout.box()

    # Main row with collapse/expand toggle, enabled, chord, label, and remove button
    r = item_box.row(align=True)

    # Selection checkbox (only visible in selection mode)
    if prefs.selection_mode:
        r.prop(m, "selected", text="")

    # Collapse/expand toggle button
    r.prop(
        m, "expanded",
        icon="TRIA_DOWN" if is_expanded else "TRIA_RIGHT",
        text="",
        emboss=False,
    )

    r.prop(m, "enabled", text="")

    # Chord field - highlight if conflicted
    chord_cell = r.row(align=True)
    chord_cell.scale_x = 0.65
    # Use all mappings if provided, otherwise fall back to prefs.mappings
    mappings_to_check = all_mappings if all_mappings is not None else prefs.mappings
    is_conflicted = _is_mapping_conflicted(m, mappings_to_check)
    # Always set alert state explicitly (don't rely on previous state)
    chord_cell.alert = is_conflicted
    chord_cell.prop(m, "chord", text="", icon="NODE_SOCKET_MATERIAL" if is_conflicted else "NODE_SOCKET_GEOMETRY")

    r.separator()
    r.scale_x = 1.5
    r.prop(m, "label", text="", icon="OUTLINER_OB_FONT")
    r.separator()

    # Group selection with searchable dropdown (now supports new group creation)
    r.prop(m, "group", text="", icon="FILE_FOLDER")

    r.separator(factor=1.5)

    # Icon display and selection button (compact)
    icon_sub = r.row(align=True)
    # icon_sub.label(text="Icon:")
    icon_sub.scale_x = 0.6
    icon_sub.prop(m, "icon", text="Icon")
    icon_sub.separator()
    op = r.operator("chordsong.icon_select", text="", icon="DOWNARROW_HLT", emboss=False)
    op.mapping_index = idx
    
    r.separator()
    
    # Move up/down buttons
    op = r.operator("chordsong.mapping_move_up", text="", icon="TRIA_UP", emboss=True)
    op.chord = getattr(m, "chord", "")
    op = r.operator("chordsong.mapping_move_down", text="", icon="TRIA_DOWN", emboss=True)
    op.chord = getattr(m, "chord", "")
    
    r.separator()
    
    op = r.operator("chordsong.mapping_copy_single", text="", icon="COPYDOWN", emboss=True)
    op.index = idx
    op = r.operator("chordsong.mapping_duplicate", text="", icon="DUPLICATE", emboss=True)
    op.index = idx
    op = r.operator("chordsong.mapping_remove", text="", icon="X", emboss=True)
    op.index = idx

    # Only show detailed content if expanded
    if not is_expanded:
        return

    # Draw context and type dropdown selectors
    r2 = _draw_dropdowns(
        item_box,
        m,
        split_factor=0.33,
        left_padding=0.0,
        separator_factor=0.8,
        context_scale=1.4,
        type_scale=1
    )

    if m.mapping_type == "PYTHON_FILE":
        # Only show Python mapping fields if custom scripts are enabled
        if prefs.allow_custom_user_scripts:
            _draw_python_mapping(r2, m, idx)
        else:
            # Show disabled message instead
            disabled_box = r2.box()
            disabled_box.alert = True
            disabled_box.label(text="Script execution is disabled")
            disabled_box.label(text="Enable 'Allow Custom User Scripts' in Preferences")
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
        split.label(text="Property:" if is_primary else "")
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
            op = btns_split.operator("chordsong.subitem_add", text="", icon="ADD")
            op.mapping_index = idx
        else:
            op = btns_split.operator("chordsong.subitem_remove", text="", icon="TRASH")
            op.mapping_index = idx
            op.item_index = sub_idx

        conv = btns_split.operator("chordsong.property_mapping_convert", text="", icon="FILE_REFRESH")
        conv.index = idx
        conv.sub_index = sub_idx

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
        split1.label(text="Property:" if is_primary else "")
        split1.prop(path_ptr, path_prop, text="")

        # Value
        row2 = inputs_col.row(align=True)
        split2 = row2.split(factor=gutter_f, align=True)
        split2.alignment = 'RIGHT'
        split2.label(text="Value:" if is_primary else "")
        split2.prop(val_ptr, val_prop, text="")

        # Right side
        controls_row = master_split.row(align=True)
        ctx_split = controls_row.split(factor=0.4, align=True)
        ctx_split.label(text="") # Placeholder

        btns_split = ctx_split.split(factor=0.5, align=True)
        if is_primary:
            op = btns_split.operator("chordsong.subitem_add", text="", icon="ADD")
            op.mapping_index = idx
        else:
            op = btns_split.operator("chordsong.subitem_remove", text="", icon="TRASH")
            op.mapping_index = idx
            op.item_index = sub_idx

        conv = btns_split.operator("chordsong.property_mapping_convert", text="", icon="FILE_REFRESH")
        conv.index = idx
        conv.sub_index = sub_idx

        op_block.separator(factor=0.4)

    draw_row(m, "context_path", m, "property_value", True)
    for i, item in enumerate(m.sub_items):
        draw_row(item, "path", item, "value", False, i)



def _draw_operator_mapping(layout, m, idx):
    """Draw rows for an operator mapping."""
    op_area = layout.box()

    master_f = 0.7
    gutter_f = 0.2
    ctx_f = 0.4

    def draw_row(container, label, ptr, prop, controls_cb=None):
        block = container.column(align=True)
        master_split = block.split(factor=master_f, align=True)

        inputs_col = master_split.column(align=True)
        row = inputs_col.row(align=True)
        split = row.split(factor=gutter_f, align=True)
        split.alignment = 'RIGHT'
        split.label(text=label)
        split.prop(ptr, prop, text="")

        controls = master_split.row(align=True)
        ctx = controls.split(factor=ctx_f, align=True)
        if controls_cb:
            controls_cb(ctx)
        else:
            ctx.label(text="")

        block.separator(factor=0.2)

    def draw_operator_block(container, op_ptr, is_primary, operator_index, sub_idx=-1):
        # Operator row (includes call context + add/remove operator + convert)
        def operator_controls(ctx):
            ctx.prop(op_ptr, "call_context", text="")
            btns = ctx.split(factor=0.5, align=True)
            if is_primary:
                op_add = btns.operator("chordsong.subitem_add", text="", icon="ADD")
                op_add.mapping_index = idx
            else:
                rem = btns.operator("chordsong.subitem_remove", text="", icon="TRASH")
                rem.mapping_index = idx
                rem.item_index = sub_idx

            conv = btns.operator("chordsong.mapping_convert", text="", icon="FILE_REFRESH")
            conv.index = idx
            conv.sub_index = sub_idx

        # Custom operator field row: keep refresh button next to the text field
        op_block = container.column(align=True)
        master_split = op_block.split(factor=master_f, align=True)
        inputs_col = master_split.column(align=True)
        id_row = inputs_col.row(align=True)
        id_split = id_row.split(factor=gutter_f, align=True)
        id_split.alignment = 'RIGHT'
        id_split.label(text="Operator:")
        op_field_split = id_split.split(factor=0.92, align=True)
        op_field_split.prop(op_ptr, "operator", text="")
        op_field_split.operator("chordsong.clear_operator_cache", text="", icon="DOT", emboss=False)

        controls = master_split.row(align=True)
        ctx = controls.split(factor=ctx_f, align=True)
        operator_controls(ctx)
        op_block.separator(factor=0.2)

        # Parameters main row (kwargs_json) + "+" to add parameter rows
        def params_controls(ctx):
            ctx.label(text="")  # Placeholder to align with call context above
            btns = ctx.split(factor=0.5, align=True)
            op_add = btns.operator("chordsong.operator_param_add", text="", icon="ADD")
            op_add.mapping_index = idx
            op_add.operator_index = operator_index
            btns.label(text="")  # Placeholder for Convert column

        draw_row(container, "Parameters:", op_ptr, "kwargs_json", params_controls)

        # Additional operator parameter rows
        for p_i, p in enumerate(getattr(op_ptr, "operator_params", [])):
            def param_row_controls(ctx, _p_i=p_i):
                ctx.label(text="")  # Placeholder
                btns = ctx.split(factor=0.5, align=True)
                rem = btns.operator("chordsong.operator_param_remove", text="", icon="TRASH")
                rem.mapping_index = idx
                rem.operator_index = operator_index
                rem.param_index = _p_i
                btns.label(text="")  # Placeholder

            draw_row(container, "", p, "value", param_row_controls)

    draw_operator_block(op_area, m, True, operator_index=0, sub_idx=-1)
    for i, sub_op in enumerate(m.sub_operators):
        draw_operator_block(op_area, sub_op, False, operator_index=i + 1, sub_idx=i)
