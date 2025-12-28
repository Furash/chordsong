"""
Addon Preferences UI layout.
"""

# pylint: disable=import-outside-toplevel

def draw_addon_preferences(prefs, _context, layout):
    """Draw the addon preferences UI."""
    prefs.ensure_defaults()

    col = layout.column()

    # "Tabs" (simple enum switch)
    col.row(align=True).prop(prefs, "prefs_tab", expand=True)

    # Config box
    box = col.box()
    header = box.row()
    header.alignment = 'CENTER'
    header.label(text="  C O N F I G  ")
    r = box.row()
    r.scale_x = 0.4
    r.label(text="Config Path:")
    r.scale_x = 4
    r.prop(prefs, "config_path", text="", icon="FILE_CACHE")
    r = box.row()
    r.scale_x = 0.4
    r.label(text="Scripts Folder:")
    r.scale_x = 4
    r.prop(prefs, "scripts_folder", text="", icon="FILE_FOLDER")
    r = box.row(align=True)
    r.operator("chordsong.save_config", text="Save Config", icon="FILE_TICK")
    r.separator()
    r.operator("chordsong.load_config", text="Load Config", icon="FILE_FOLDER")
    r.separator()
    r.operator("chordsong.load_default", text="Load Default Config", icon="LOOP_BACK")
    r.separator()
    r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")
    box.separator()

    if prefs.prefs_tab == "UI":
        # Section: Global Visibility
        box = col.box()
        header = box.row()
        header.label(text="Display Control", icon='HIDE_OFF')
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_enabled", toggle=True, text="Global Overlay Visibility")
        r.prop(prefs, "overlay_fading_enabled", toggle=True, text="Enable Fading Overlay")
        r = box.row(align=True)
        r.prop(prefs, "overlay_show_header", toggle=True, text="Show Header")
        r.prop(prefs, "overlay_show_footer", toggle=True, text="Show Footer")

        # Section: Layout & Items
        box = col.box()
        header = box.row()
        header.label(text="Layout & Items", icon='MOD_LENGTH')
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_max_items", text="Max Items")
        r.prop(prefs, "overlay_column_rows", text="Rows per Column")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_gap", text="Vertical Gap")
        r.prop(prefs, "overlay_line_height", text="Line Height")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_column_gap", text="Horizontal Column Gap")

        # Section: Typography
        box = col.box()
        header = box.row()
        header.label(text="Typography", icon='FONT_DATA')
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_header", text="Header Size")
        r.prop(prefs, "overlay_font_size_chord", text="Chord Size")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_body", text="Body Size")
        r.prop(prefs, "overlay_font_size_footer", text="Footer Size")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_fading", text="Fading Font Size")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_toggle", text="Toggle Icon Size")
        r.prop(prefs, "overlay_toggle_offset_y", text="Vertical Offset")

        # Section: Positioning
        box = col.box()
        header = box.row()
        header.label(text="Positioning", icon='CURSOR')
        
        box.prop(prefs, "overlay_position", text="Anchor Position")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_offset_x", text="X Offset")
        r.prop(prefs, "overlay_offset_y", text="Y Offset")

        # Section: Footer Fine-Tuning
        box = col.box()
        header = box.row()
        header.label(text="Footer Fine-Tuning", icon='ALIGN_BOTTOM')
        
        box.prop(prefs, "overlay_footer_gap", text="Space Between Footer Items")
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_footer_token_gap", text="Inner Token Gap")
        r.prop(prefs, "overlay_footer_label_gap", text="Inner Label Gap")

        # Section: Appearance & Theme
        box = col.box()
        header = box.row()
        header.label(text="Appearance", icon='BRUSH_DATA')
        
        r = box.row(align=True)
        r.label(text="Folder Display Style:")
        r.prop(prefs, "overlay_folder_style", text="")
        box.separator()

        # Color table logic
        split = box.split(factor=0.3)
        col1 = split.column()
        col2 = split.column()
        
        # Labels and Pickers grouped together
        for label, prop in [
            ("Chord Color", "overlay_color_chord"),
            ("Label Color", "overlay_color_label"),
            ("Icon Color", "overlay_color_icon"),
            ("Toggle ON", "overlay_color_toggle_on"),
            ("Toggle OFF", "overlay_color_toggle_off"),
            ("Header Text", "overlay_color_header"),
            ("Recents Key", "overlay_color_recents_hotkey"),
            ("List Background", "overlay_list_background"),
            ("Header Background", "overlay_header_background"),
            ("Footer Background", "overlay_footer_background"),
        ]:
            col1.label(text=label)
            col2.prop(prefs, prop, text="")

        # Testing Section
        box_test = col.box()
        header = box_test.row()
        header.label(text="Debug Tools", icon='TOOL_SETTINGS')
        row = box_test.row()
        row.operator("chordsong.test_main_overlay", text="Preview Main", icon="PLAY")
        row.operator("chordsong.test_fading_overlay", text="Preview Fading", icon="PLAY")

        return

    # MAPPINGS tab
    # Keymap section
    kc = _context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.get("3D View")
        if km:
            # Find the leader keymap item
            kmi = None
            for item in km.keymap_items:
                if item.idname == "chordsong.leader":
                    kmi = item
                    break

            if kmi:
                box = col.box()
                split = box.split(factor=0.5)

                # Leader Key section
                leader_col = split.column()
                leader_row = leader_col.row(align=True)
                leader_row.scale_y = 1.2
                leader_row.label(text="Leader Key:")
                leader_row.scale_y = 1.5
                leader_row.scale_x = 1.5
                leader_row.context_pointer_set("keymap", km)
                leader_row.prop(kmi, "type", text="", full_event=True, emboss=True)
                leader_row.separator()

                # Conflict checker section
                conflict_col = split.column()
                conflict_row = conflict_col.row(align=True)
                conflict_row.scale_y = 1.2
                conflict_row.label(text="Conflict Checker:")
                conflict_row.scale_y = 1.5
                conflict_row.operator("chordsong.check_conflicts", text="Check for Conflicts", icon="ERROR")

                box.separator()

    # Context sub-tabs
    row = col.row(align=True)
    row.prop(prefs, "mapping_context_tab", expand=True)
    col.separator()

    row = col.row(align=True)
    row.scale_y = 1.5
    op = row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    op.context = prefs.mapping_context_tab
    
    # row = col.row(align=True)
    # row.scale_y = 1.5
    row.separator()
    op = row.operator("chordsong.group_add", text="Add New Group", icon="ADD")
    op.name = "New Group"
    row.separator()
    row.operator("chordsong.group_cleanup", text="", icon="BRUSH_DATA")
    row.separator()
    row.operator("chordsong.group_fold_all", text="", icon="TRIA_UP")
    row.operator("chordsong.group_unfold_all", text="", icon="TRIA_DOWN")

    # Grouped UI boxes with foldable sections
    from ..core.engine import get_str_attr

    # Filter mappings by selected context tab
    current_context = prefs.mapping_context_tab

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        # Filter by context
        mapping_context = getattr(m, "context", "VIEW_3D")
        if mapping_context != current_context:
            continue

        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    # Note: We only show groups that have mappings in the current context
    # Empty groups from other contexts are not displayed

    for group_name in sorted(groups.keys(), key=lambda s: (s != "Ungrouped", s.lower())):
        items = groups[group_name]
        items.sort(
            key=lambda im: (
                get_str_attr(im[1], "chord").lower(),
                get_str_attr(im[1], "label").lower(),
            )
        )

        # Find the group object to get expanded state
        if group_name == "Ungrouped":
            # Use prefs-level property for ungrouped
            is_expanded = prefs.ungrouped_expanded
            expand_data = prefs
            expand_prop = "ungrouped_expanded"
        else:
            # Find the group in the groups collection
            grp_obj = None
            for grp in prefs.groups:
                if grp.name == group_name:
                    grp_obj = grp
                    break
            if grp_obj:
                is_expanded = grp_obj.expanded
                expand_data = grp_obj
                expand_prop = "expanded"
            else:
                # Group not found (shouldn't happen), default to expanded
                is_expanded = True
                expand_data = None
                expand_prop = None

        box = col.box()

        # Foldable header row
        header = box.row(align=True)
        if expand_data and expand_prop:
            header.prop(
                expand_data, expand_prop,
                icon="TRIA_DOWN" if is_expanded else "TRIA_RIGHT",
                text="",
                emboss=False,
            )
        header.label(text=f"{group_name}")

        # Add new chord button in header
        op = header.operator("chordsong.mapping_add", text="", icon="ADD")
        op.group = group_name
        op.context = prefs.mapping_context_tab
        header.separator()

        # Delete group button (only for non-Ungrouped groups)
        if group_name != "Ungrouped":
            # Find the group index
            group_idx = None
            for idx, grp in enumerate(prefs.groups):
                if grp.name == group_name:
                    group_idx = idx
                    break

            if group_idx is not None:
                op = header.operator("chordsong.group_remove", text="", icon="TRASH", emboss=False)
                op.index = group_idx

        if not is_expanded:
            continue

        box.separator()

        for idx, m in items:
            # Wrap each mapping in its own box for clear visual separation
            item_box = box.box()
            
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
            # This allows us to nudge the icons down slightly to align with the box contents
            r2_split = row2.split(factor=0.21, align=True)
            
            # Left side: Icons (nudged down for better alignment with box text)
            icon_col = r2_split.column()
            icon_col.separator(factor=0.5)
            icon_row = icon_col.row(align=True)
            
            # Context selector (icon-only)
            icon_row.prop_enum(m, "context", "VIEW_3D", icon="VIEW3D", text="")
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
            
            # Right side: Type-specific fields (Toggles, Properties, etc.)
            r2 = r2_split.column()

            if m.mapping_type == "PYTHON_FILE":
                # For script, we don't need a box, but we need horizontal alignment
                script_row = r2.row(align=True)
                script_row.prop(m, "python_file", text="")
                script_row.separator()
                op = script_row.operator("chordsong.script_select", text="Select Script", icon="FILEBROWSER", emboss=True)
                op.mapping_index = idx
                
            elif m.mapping_type == "CONTEXT_TOGGLE":
                # Create a box for all toggles
                
                def draw_toggle_row_fixed(layout, path_ptr, path_prop, is_primary, m, idx, sub_idx=-1):
                    row = layout.row(align=True)
                    # Use a fixed split to align primary row and sub-items perfectly
                    # Path column (approx 75%)
                    p_split = row.split(factor=0.75, align=True)
                    p_split.prop(path_ptr, path_prop, text="")
                    
                    # Remaining 25% for Icon + Button
                    # Split that 25% into 12% for icon (~3% total) and 88% for button (~22% total)
                    b_split = p_split.split(factor=0.12, align=True)
                    
                    # Sync toggles flag - shown on EVERY row, sharing the same state
                    b_split.prop(m, "sync_toggles", text="", icon='LINKED' if m.sync_toggles else 'UNLINKED', toggle=True)

                    if is_primary:
                        op = b_split.operator("chordsong.subitem_add", text="Add Property", icon="ADD")
                        op.mapping_index = idx
                    else:
                        rem = b_split.operator("chordsong.subitem_remove", text="Remove Property", icon="TRASH")
                        rem.mapping_index = idx
                        rem.item_index = sub_idx

                # Draw rows using the fixed layout helper
                draw_toggle_row_fixed(r2, m, "context_path", True, m, idx)
                for i, item in enumerate(m.sub_items):
                    draw_toggle_row_fixed(r2, item, "path", False, m, idx, i)

            elif m.mapping_type == "CONTEXT_PROPERTY":
                # Create a common box for all property rows
                prop_area = r2.box()
                
                # Layout helper for property rows within the box
                def draw_prop_row(layout, path_ptr, path_prop, val_ptr, val_prop, is_primary, sub_idx=-1):
                    row = layout.row(align=True)
                    
                    # Rebalanced splits
                    path_split = row.split(factor=0.35, align=True)
                    path_split.prop(path_ptr, path_prop, text="")
                    
                    val_split = path_split.split(factor=0.5, align=True)
                    val_split.prop(val_ptr, val_prop, text="Value")
                    
                    btn_row = val_split.row(align=True)
                    
                    # Convert button
                    conv = btn_row.operator("chordsong.property_mapping_convert", text="Convert", icon="SOLO_ON")
                    conv.index = idx
                    conv.sub_index = sub_idx

                    # Add/Remove button
                    if is_primary:
                        op_add = btn_row.operator("chordsong.subitem_add", text="Add", icon="ADD")
                        op_add.mapping_index = idx
                    else:
                        rem = btn_row.operator("chordsong.subitem_remove", text="Remove", icon="TRASH")
                        rem.mapping_index = idx
                        rem.item_index = sub_idx
                    

                # Draw first row in the box
                draw_prop_row(prop_area, m, "context_path", m, "property_value", True)
                
                # Draw sub-items in the same box
                for i, item in enumerate(m.sub_items):
                    draw_prop_row(prop_area, item, "path", item, "value", False, i)
            else:
                # Group all operators and their parameters in a common box
                op_area = r2.box()
                
                # Layout helper for operator rows within the box
                def draw_op_row(layout, m_ptr, op_prop, ctx_prop, kwargs_prop, is_primary, sub_idx=-1):
                    # Outer column for the operator block
                    op_block = layout.column(align=True)
                    
                    # Split for Inputs (Left) vs Controls (Right)
                    # Use a fixed factor (0.7) to give more room for names and params
                    master_split = op_block.split(factor=0.7, align=True)
                    
                    # 1. LEFT PORTION: The "What" (Operator ID & Parameters)
                    inputs_col = master_split.column(align=True)
                    
                    # To align the Operator field with the Parameters field, we use a gutter split
                    # factor 0.2 is enough for the "Operator:" and "Parameters:" text
                    gutter_f = 0.2
                    
                    # Row 1: Operator ID
                    id_row = inputs_col.row(align=True)
                    id_split = id_row.split(factor=gutter_f, align=True)
                    id_split.alignment = 'RIGHT'
                    id_split.label(text="Operator:") 
                    id_split.prop(m_ptr, op_prop, text="")
                    
                    # Row 2: Parameters
                    p_row = inputs_col.row(align=True)
                    p_split = p_row.split(factor=gutter_f, align=True)
                    p_split.alignment = 'RIGHT'
                    p_split.label(text="Parameters:")
                    p_split.prop(m_ptr, kwargs_prop, text="")
                    
                    # 2. RIGHT PORTION: The "How" (Invoke, Add/Del, Convert)
                    controls_row = master_split.row(align=True)
                    
                    # Split 1: Context Enum (Exec/Invoke)
                    # We give it a fixed width via split.
                    ctx_split = controls_row.split(factor=0.4, align=True)
                    ctx_split.prop(m_ptr, ctx_prop, text="")
                    
                    # Remaining space split in half for the two buttons
                    btns_split = ctx_split.split(factor=0.5, align=True)
                    
                    if is_primary:
                        op_add = btns_split.operator("chordsong.subitem_add", text="Add", icon="ADD")
                        op_add.mapping_index = idx
                    else:
                        rem = btns_split.operator("chordsong.subitem_remove", text="Del", icon="TRASH")
                        rem.mapping_index = idx
                        rem.item_index = sub_idx
                    
                    # Convert button
                    conv = btns_split.operator("chordsong.mapping_convert", text="Convert")
                    conv.index = idx
                    conv.sub_index = sub_idx
                    
                    # Visual separation
                    layout.separator(factor=0.4)

                # Draw the primary operator row
                draw_op_row(op_area, m, "operator", "call_context", "kwargs_json", True)

                # Draw all sub-operator rows
                for i, sub_op in enumerate(m.sub_operators):
                    draw_op_row(op_area, sub_op, "operator", "call_context", "kwargs_json", False, i)
            
            # Extra spacing between item boxes
            box.separator(factor=2.0)

    col.separator()
