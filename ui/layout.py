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
        # Overlay settings
        box = col.box()
        
        # Toggles row
        r = box.row(align=True)
        r.prop(prefs, "overlay_enabled", toggle=True)
        r.separator()
        r.prop(prefs, "overlay_fading_enabled", toggle=True, text="Fading")
        r.separator()
        r.prop(prefs, "overlay_show_header", toggle=True, text="Header")
        r.separator()
        r.prop(prefs, "overlay_show_footer", toggle=True, text="Footer")
        
        # Counts
        r = box.row(align=True)
        r.prop(prefs, "overlay_max_items")
        r.separator()
        r.prop(prefs, "overlay_column_rows")

        
        # Font sizes
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_header", text="Header Size")
        r.prop(prefs, "overlay_font_size_footer", text="Footer Size")

        box.separator()
        
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_chord")
        r.prop(prefs, "overlay_font_size_body")
        r.prop(prefs, "overlay_font_size_fading")

        
        # Layout settings
        r = box.row(align=True)
        r.prop(prefs, "overlay_gap", text="Element Gap")
        r.prop(prefs, "overlay_column_gap", text="Column Gap")
        r.prop(prefs, "overlay_line_height", text="Line Height")
        r = box.row(align=True)
        r.prop(prefs, "overlay_footer_gap", text="Footer Item Gap")
        r.prop(prefs, "overlay_footer_token_gap", text="Footer Token Gap")
        r.prop(prefs, "overlay_footer_label_gap", text="Footer Label Gap")

        # Position settings
        r = box.row(align=True)
        r.label(text="Position:")
        r.scale_x = 2.5
        r.prop(prefs, "overlay_position", text="")
        r.separator()
        r.prop(prefs, "overlay_offset_x")
        r.separator()
        r.prop(prefs, "overlay_offset_y")
        box.separator()

        # Color settings
        split = box.split(factor=0.11)
        col1 = split.column()
        col2 = split.column()
        col3 = split.column()
        col4 = split.column()
        col5 = split.column()
        
        # First column - labels
        col1.label(text="Chord:")
        col1.label(text="Label:")
        col1.label(text="Icon:")
        col1.label(text="Header:")
        col1.label(text="Recents Hotkey:")
        col1.label(text="List Background:")
        col1.label(text="Header Background:")
        col1.label(text="Footer Background:")
        
        # Second column - color pickers
        col2.prop(prefs, "overlay_color_chord", text="")
        col2.prop(prefs, "overlay_color_label", text="")
        col2.prop(prefs, "overlay_color_icon", text="")
        col2.prop(prefs, "overlay_color_header", text="")
        col2.prop(prefs, "overlay_color_recents_hotkey", text="")
        col2.prop(prefs, "overlay_list_background", text="")
        col2.prop(prefs, "overlay_header_background", text="")
        col2.prop(prefs, "overlay_footer_background", text="")
        
        col3.separator()
        col4.separator()
        col5.separator()

        # Testing
        box_test = col.box()
        box_test.label(text="Testing")
        row = box_test.row()
        row.operator("chordsong.test_main_overlay", text="Test Main Overlay", icon="PLAY")
        row.operator("chordsong.test_fading_overlay", text="Test Fading Overlay", icon="PLAY")
        
        box.separator()

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
    row.operator("chordsong.group_cleanup", text="", icon="BRUSH_DATA")
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
            # Main row with enabled, chord, label, and remove button
            r = box.row(align=True)
            r.prop(m, "enabled", text="")
            r.scale_x = 0.5
            r.prop(m, "chord", text="")
            r.separator()
            r.scale_x = 1.5
            r.prop(m, "label", text="")
            r.separator()

            # Group selection with searchable dropdown
            r.prop_search(m, "group", prefs, "groups", icon="FILE_FOLDER", text="")
            
            # Button to create new group
            op = r.operator("chordsong.group_add", text="", icon="ADD", emboss=True)
            op.name = "New Group"
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
            r2 = box.row(align=True)
            # Context selector (icon-only)
            r2.prop_enum(m, "context", "VIEW_3D", icon="VIEW3D", text="")
            r2.separator()
            r2.prop_enum(m, "context", "GEOMETRY_NODE", icon="GEOMETRY_NODES", text="")
            r2.separator()
            r2.prop_enum(m, "context", "SHADER_EDITOR", icon="NODE_MATERIAL", text="")
            r2.separator()
            r2.prop_enum(m, "context", "IMAGE_EDITOR", icon="UV", text="")
            r2.separator()
            r2.separator()
            # Icon-only mapping type selector
            r2.prop_enum(m, "mapping_type", "OPERATOR", icon="SETTINGS", text="")
            r2.separator()
            r2.prop_enum(m, "mapping_type", "PYTHON_FILE", icon="FILE_SCRIPT", text="")
            r2.separator()
            r2.prop_enum(m, "mapping_type", "CONTEXT_TOGGLE", icon="CHECKBOX_HLT", text="")
            r2.separator()

            if m.mapping_type == "PYTHON_FILE":
                r2.prop(m, "python_file", text="")
                r2.separator()
                # Script selector button
                op = r2.operator("chordsong.script_select", text="Select Script", icon="FILEBROWSER", emboss=True)
                op.mapping_index = idx
            elif m.mapping_type == "CONTEXT_TOGGLE":
                r2.prop(m, "context_path", text="")
            else:
                r2.prop(m, "operator", text="")
                # Small convert button - create subsection with tight scaling
                sub = r2.row(align=True)
                sub.separator()
                sub.scale_x = 0.9
                sub.alignment = 'LEFT'
                op_convert = sub.operator("chordsong.mapping_convert", text="Convert", emboss=True)
                op_convert.index = idx
                # Call context selector (EXEC vs INVOKE)
                sub.separator()
                sub.prop(m, "call_context", text="")

            # Third row for parameters (only for operator type)
            if m.mapping_type == "OPERATOR":
                r3 = box.row()
                r3.label(text="Parameters:")
                r3.scale_x = 8
                r3.prop(m, "kwargs_json", text="")
                box.separator()

    col.separator()
