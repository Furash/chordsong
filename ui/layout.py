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
    col.separator()

    # Config box
    box = col.box()
    header = box.row()
    header.alignment = 'CENTER'
    header.label(text="C O N F I G")
    box.separator()
    r = box.row(align=True)
    r.prop(prefs, "config_path")
    r = box.row(align=True)
    r.operator("chordsong.save_config", text="Save Config", icon="FILE_TICK")
    r.separator()
    r.operator("chordsong.load_config", text="Load Config", icon="FILE_FOLDER")
    r.separator()
    r.operator("chordsong.load_default", text="Load Default Config", icon="LOOP_BACK")
    r.separator()
    r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")

    if prefs.prefs_tab == "GROUPS":
        # Groups management tab
        box = col.box()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text=f"GROUPS ({len(prefs.groups)})")
        box.separator()

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
                # Group name (editable inline)
                row.prop(grp, "name", text="")

                # Mapping count badge
                sub = row.row(align=True)
                sub.scale_x = 0.6
                sub.label(text=f"({count})")

                # Rename button
                op = row.operator(
                    "chordsong.group_rename", text="", icon="GREASEPENCIL", emboss=False
                )
                op.index = idx

                # Remove button
                op = row.operator("chordsong.group_remove", text="", icon="X", emboss=False)
                op.index = idx

                box.separator()

        return

    if prefs.prefs_tab == "UI":
        box = col.box()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text="Overlay")
        box.separator()

        r = box.row(align=True)
        r.prop(prefs, "overlay_enabled")
        r.prop(prefs, "overlay_max_items")
        r.prop(prefs, "overlay_column_rows")
        box.separator()

        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_header")
        r.prop(prefs, "overlay_font_size_chord")
        r.prop(prefs, "overlay_font_size_body")

        box.separator()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text="Colors")
        box.separator()
        r = box.row(align=True)
        r.prop(prefs, "overlay_color_chord", text="Chord")
        r.prop(prefs, "overlay_color_label", text="Label")
        box.separator()
        r = box.row(align=True)
        r.prop(prefs, "overlay_color_header", text="Header")

        box.separator()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text="Position")
        box.separator()
        r = box.row(align=True)
        r.prop(prefs, "overlay_position", text="")
        box.separator()
        r = box.row(align=True)
        r.prop(prefs, "overlay_offset_x")
        r.prop(prefs, "overlay_offset_y")

        col.separator()
        box = col.box()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text="Modal")
        box.separator()
        box.prop(prefs, "timeout_ms")

        return

    # MAPPINGS tab
    row = col.row(align=True)
    row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    row.separator()
    row.prop(prefs, "timeout_ms")
    # actions_row = col.row(align=True)

    # Grouped UI boxes
    from ..core.engine import get_str_attr

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    for group_name in sorted(groups.keys(), key=lambda s: (s == "Ungrouped", s.lower())):
        box = col.box()
        header = box.row()
        header.alignment = 'CENTER'
        header.label(text=group_name)
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
            r.separator()
            r.prop(m, "chord", text="")
            r.separator()
            r.prop(m, "label", text="")
            r.separator()
            op = r.operator("chordsong.mapping_remove", text="", icon="X", emboss=False)
            op.index = idx
            box.separator()

            # Icon and Group row
            r_meta = box.row(align=True)
            r_meta.prop(m, "icon", text="Icon", icon="IMAGE_DATA")
            r_meta.separator()
            r_meta.prop(m, "group", text="Group", icon="NEWFOLDER")
            # Add a button for quick group selection from existing groups
            if prefs.groups:
                op = r_meta.operator("chordsong.group_select", text="", icon="DOWNARROW_HLT")
                op.mapping_index = idx
            box.separator()

            # Second row with type selector and type-specific fields
            r2 = box.row(align=True)
            # Icon-only mapping type selector
            r2.prop_enum(m, "mapping_type", "OPERATOR", icon="SETTINGS", text="")
            r2.prop_enum(m, "mapping_type", "PYTHON_FILE", icon="FILE_SCRIPT", text="")

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
                r3.prop(m, "kwargs_json", text="Parameters")
                box.separator()

    col.separator()
