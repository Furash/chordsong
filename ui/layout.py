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
    r = box.row(align=True)
    r.operator("chordsong.save_config", text="Save Config", icon="FILE_TICK")
    r.separator()
    r.operator("chordsong.load_config", text="Load Config", icon="FILE_FOLDER")
    r.separator()
    r.operator("chordsong.load_default", text="Load Default Config", icon="LOOP_BACK")
    r.separator()
    r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")
    box.separator()

    if prefs.prefs_tab == "GROUPS":
        # Groups management tab
        box = col.box()
        # header = box.row()
        # header.alignment = 'CENTER'
        # header.label(text="GROUPS")
        # box.separator()

        # Add new group and cleanup buttons
        row = box.row(align=True)
        row.operator("chordsong.group_add", text="Add New Group", icon="ADD")
        row.operator("chordsong.group_cleanup", text="Clean Up Duplicates", icon="BRUSH_DATA")
        box.separator()

        if not prefs.groups:
            box.label(text="No groups defined yet")
            box.label(text="Groups are auto-created from mappings")
        else:
            # List all groups
            for idx, grp in enumerate(prefs.groups):
                # Count mappings using this group
                count = sum(1 for m in prefs.mappings if m.group == grp.name)

                row = box.row(align=True)
                row.scale_x = 0.8
                # Group name (editable inline)
                row.prop(grp, "name", text="")
                row.separator()

                # Mapping count badge
                sub = row.row(align=True)
                sub.scale_x = 0.2
                sub.label(text=f"({count})")

                # Remove button
                op = row.operator("chordsong.group_remove", text="", icon="X", emboss=True)
                op.index = idx

                box.separator()

        return

    if prefs.prefs_tab == "UI":
        # Overlay settings
        box = col.box()
        r = box.row(align=True)
        r.prop(prefs, "overlay_enabled", toggle=True)
        r.separator()
        r.prop(prefs, "overlay_max_items")
        r.separator()
        r.prop(prefs, "overlay_column_rows")
        r.separator()
        box.separator()

        # Font size settings
        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_header")
        r.separator()
        r.prop(prefs, "overlay_font_size_chord")
        r.separator()
        r.prop(prefs, "overlay_font_size_body")
        box.separator()

        # Position settings
        r = box.row(align=True)
        r.prop(prefs, "overlay_position", text="")
        r.separator()
        r.prop(prefs, "overlay_offset_x")
        r.separator()
        r.prop(prefs, "overlay_offset_y")
        box.separator()

        # Color settings
        r = box.row(align=True)
        r.prop(prefs, "overlay_color_chord", text="Chord")
        r.separator()
        r.prop(prefs, "overlay_color_label", text="Label")
        r.separator()
        r.prop(prefs, "overlay_color_header", text="Header")
        r.separator()
        r.prop(prefs, "overlay_color_icon", text="Icon")
        box.separator()


        return

    # MAPPINGS tab
    row = col.row(align=True)
    row.scale_y = 2
    row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    # actions_row = col.row(align=True)

    # Grouped UI boxes
    from ..core.engine import get_str_attr

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    for group_name in sorted(groups.keys(), key=lambda s: (s != "Ungrouped", s.lower())):
        box = col.box()
        box.separator()
        items = groups[group_name]
        items.sort(
            key=lambda im: (
                get_str_attr(im[1], "label").lower(),
                get_str_attr(im[1], "chord").lower(),
            )
        )

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
            # Icon and Group row
            # r_meta = box.row(align=True)
            
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

            # Second row with type selector and type-specific fields
            r2 = box.row(align=True)
            # Icon-only mapping type selector
            r2.prop_enum(m, "mapping_type", "OPERATOR", icon="SETTINGS", text="")
            r2.separator()
            r2.prop_enum(m, "mapping_type", "PYTHON_FILE", icon="FILE_SCRIPT", text="")
            r2.separator()

            if m.mapping_type == "PYTHON_FILE":
                r2.prop(m, "python_file", text="")
            else:
                r2.prop(m, "operator", text="")
                # Small convert button - create subsection with tight scaling
                sub = r2.row(align=True)
                sub.separator()
                sub.scale_x = 0.9
                sub.alignment = 'LEFT'
                op_convert = sub.operator("chordsong.mapping_convert", text="Convert", emboss=True)
                op_convert.index = idx

            # Third row for parameters (only for operator type)
            if m.mapping_type == "OPERATOR":
                r3 = box.row()
                r3.label(text="Parameters:")
                r3.scale_x = 8
                r3.prop(m, "kwargs_json", text="")
                box.separator()

    col.separator()
