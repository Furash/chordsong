"""
UI tab for addon preferences.
"""

def draw_ui_tab(prefs, layout):
    """Draw the UI/Overlay customization tab."""
    # Section: Global Visibility
    box = layout.box()
    header = box.row()
    header.label(text="Display Control", icon='HIDE_OFF')
    
    r = box.row(align=True)
    r.prop(prefs, "overlay_enabled", toggle=True, text="Global Overlay Visibility")
    r.prop(prefs, "overlay_fading_enabled", toggle=True, text="Enable Fading Overlay")
    r = box.row(align=True)
    r.prop(prefs, "overlay_show_header", toggle=True, text="Show Header")
    r.prop(prefs, "overlay_show_footer", toggle=True, text="Show Footer")

    # Section: Layout & Items
    box = layout.box()
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
    box = layout.box()
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
    r.prop(prefs, "overlay_toggle_offset_y", text="Toggle Vertical Offset")

    # Section: Positioning
    box = layout.box()
    header = box.row()
    header.label(text="Positioning", icon='CURSOR')
    
    box.prop(prefs, "overlay_position", text="Anchor Position")
    
    r = box.row(align=True)
    r.prop(prefs, "overlay_offset_x", text="X Offset")
    r.prop(prefs, "overlay_offset_y", text="Y Offset")

    # Section: Footer Fine-Tuning
    box = layout.box()
    header = box.row()
    header.label(text="Footer Fine-Tuning", icon='ALIGN_BOTTOM')
    
    box.prop(prefs, "overlay_footer_gap", text="Space Between Footer Items")
    
    r = box.row(align=True)
    r.prop(prefs, "overlay_footer_token_gap", text="Inner Token Gap")
    r.prop(prefs, "overlay_footer_label_gap", text="Inner Label Gap")

    # Section: Appearance & Theme
    box = layout.box()
    header = box.row()
    header.label(text="Appearance", icon='BRUSH_DATA')
    
    r = box.row(align=True)
    r.label(text="Folder Display Style:")
    r.prop(prefs, "overlay_folder_style", text="")
    box.separator()
    
    # Theme Presets Section
    theme_box = box.box()
    theme_row = theme_box.row()
    theme_row.label(text="Theme", icon='COLOR')
    
    # Extract from Blender (primary option)
    extract_row = theme_box.row()
    extract_row.scale_y = 1.5
    extract_row.operator("chordsong.extract_blender_theme", text="Match Current Blender Theme", icon='EYEDROPPER')
    
    theme_box.separator()
    
    # Import/Export and Preset
    io_row = theme_box.row(align=True)
    io_row.operator("chordsong.load_theme_preset", text="Reset to Default", icon='LOOP_BACK').preset_name = "default"
    io_row.separator()
    io_row.operator("chordsong.import_overlay_theme", text="Import", icon='IMPORT')
    io_row.separator()
    io_row.operator("chordsong.export_overlay_theme", text="Export", icon='EXPORT')
    
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
        ("Separators", "overlay_color_separator"),
        ("List Background", "overlay_list_background"),
        ("Header Background", "overlay_header_background"),
        ("Footer Background", "overlay_footer_background"),
    ]:
        col1.label(text=label)
        col2.prop(prefs, prop, text="")

    # Testing Section
    box_test = layout.box()
    header = box_test.row()
    header.label(text="Debug Tools", icon='TOOL_SETTINGS')
    row = box_test.row()
    row.operator("chordsong.test_main_overlay", text="Preview Main", icon="PLAY")
    row.operator("chordsong.test_fading_overlay", text="Preview Fading", icon="PLAY")
    row.operator("chordsong.scripts_overlay", text="Scripts Overlay", icon="FILE_SCRIPT")
