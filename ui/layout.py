"""
Addon Preferences UI layout.
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught


def _draw_leader_keymap(layout, context):
    """
    Draw the add-on keymap item for the leader operator directly in our preferences UI.
    """
    try:
        import rna_keymap_ui  # type: ignore
    except Exception:
        layout.label(text="Keymap UI module not available in this Blender build.")
        return

    wm = context.window_manager
    kc = wm.keyconfigs.addon if wm else None
    if not kc:
        layout.label(text="No add-on keyconfig available (kc.keyconfigs.addon is None).")
        return

    km = kc.keymaps.get("3D View")
    if not km:
        layout.label(text='Keymap "3D View" not found (enable the addon once to register it).')
        return

    kmi = None
    for item in km.keymap_items:
        if item.idname == "chordsong.leader":
            kmi = item
            break

    if not kmi:
        layout.label(text='Keymap item for "chordsong.leader" not found.')
        return

    # Draw the standard Blender keymap UI row.
    rna_keymap_ui.draw_kmi([], kc, km, kmi, layout, 0)


def draw_addon_preferences(prefs, context, layout):
    prefs.ensure_defaults()

    col = layout.column()

    # "Tabs" (simple enum switch)
    col.row(align=True).prop(prefs, "prefs_tab", expand=True)
    col.separator()

    if prefs.prefs_tab == "UI":
        box = col.box()
        box.label(text="Overlay")

        r = box.row(align=True)
        r.prop(prefs, "overlay_enabled")
        r.prop(prefs, "overlay_max_items")
        r.prop(prefs, "overlay_column_rows")

        r = box.row(align=True)
        r.prop(prefs, "overlay_font_size_header")
        r.prop(prefs, "overlay_font_size_chord")
        r.prop(prefs, "overlay_font_size_body")

        box.separator()
        box.label(text="Colors")
        r = box.row(align=True)
        r.prop(prefs, "overlay_color_chord", text="Chord")
        r.prop(prefs, "overlay_color_label", text="Label")
        r = box.row(align=True)
        r.prop(prefs, "overlay_color_header", text="Header")

        box.separator()
        box.label(text="Position")
        r = box.row(align=True)
        r.prop(prefs, "overlay_position", text="")
        r = box.row(align=True)
        r.prop(prefs, "overlay_offset_x")
        r.prop(prefs, "overlay_offset_y")

        col.separator()
        col.label(text="Modal")
        col.prop(prefs, "timeout_ms")

        col.separator()
        box = col.box()
        box.label(text="Config")
        box.prop(prefs, "config_path")
        r = box.row(align=True)
        r.operator("chordsong.save_config", text="Save User", icon="FILE_TICK")
        r.separator()           
        r.operator("chordsong.load_config", text="Load User", icon="FILE_FOLDER")
        r.separator()
        r.operator("chordsong.load_default", text="Load Default", icon="LOOP_BACK")
        r.separator()
        r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")

        return

    # MAPPINGS tab
    col.separator()
    row = col.row(align=True)
    row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    row.separator()
    row.prop(prefs, "timeout_ms")
    # actions_row = col.row(align=True)

    # Grouped UI boxes
    groups = {}
    for idx, m in enumerate(prefs.mappings):
        group = (getattr(m, "group", "") or "").strip() or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    for group_name in sorted(groups.keys(), key=lambda s: (s == "Ungrouped", s.lower())):
        box = col.box()
        box.label(text=group_name)
        items = groups[group_name]
        items.sort(
            key=lambda im: (
                (getattr(im[1], "label", "") or "").lower(),
                (getattr(im[1], "chord", "") or "").lower(),
            )
        )

        for idx, m in items:
            # Main row with enabled, chord, label, and remove button
            r = box.row(align=True)
            r.prop(m, "enabled", text="")
            r.prop(m, "chord", text="")
            r.prop(m, "label", text="")
            op = r.operator("chordsong.mapping_remove", text="", icon="X", emboss=False)
            op.index = idx
            
            # Second row with type selector and type-specific fields
            r2 = box.row(align=True)
            r2.prop(m, "mapping_type", text="")
            
            if m.mapping_type == "PYTHON_FILE":
                r2.prop(m, "python_file", text="")
            else:
                r2.prop(m, "operator", text="")
                op_convert = r2.operator("chordsong.mapping_convert", text="CONVERT", emboss=True)
                op_convert.index = idx
            
            # Third row for parameters (only for operator type)
            if m.mapping_type == "OPERATOR":
                r3 = box.row()
                r3.prop(m, "kwargs_json", text="Parameters")

    col.separator()
    box = col.box()
    box.label(text="Config")
    box.prop(prefs, "config_path")
    r = box.row(align=True)
    r.operator("chordsong.save_config", text="Save User", icon="FILE_TICK")
    r.separator()
    r.operator("chordsong.load_config", text="Load User", icon="FILE_FOLDER")
    r.separator()
    r.operator("chordsong.load_default", text="Load Default", icon="LOOP_BACK")
    r.separator()
    r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")


