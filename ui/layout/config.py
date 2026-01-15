"""
Config section for addon preferences.
"""

def draw_config_section(prefs, layout):
    """Draw the config box (save/load/autosave)."""
    box = layout.box()
    header = box.row()
    header.alignment = 'CENTER'
    header.label(text="  C O N F I G ")

    r = box.row()
    r.scale_x = 0.4
    r.label(text="Config Path:")
    r.scale_x = 4
    r.prop(prefs, "config_path", text="", icon="FILE_CACHE")

    r = box.row()
    if not prefs.allow_custom_user_scripts:
        r = box.row()
        r.alert = True
        r.label(text="Script chords are disabled", icon="ERROR")
        r.prop(prefs, "allow_custom_user_scripts", icon="SCRIPT")
    else:
        r.scale_x = 0.8
        r.label(text="Scripts Folder:")
        r.scale_x = 4
        r.prop(prefs, "scripts_folder", text="", icon="FILE_FOLDER")
        r.prop(prefs, "allow_custom_user_scripts", icon="SCRIPT")

    r = box.row(align=True)
    r.scale_y = 1.5
    r.operator("chordsong.save_config", text="Save Config", icon="FILE_TICK")
    r.separator()
    r.scale_y = 1.5
    r.operator("chordsong.export_config", text="Export Config", icon="EXPORT")
    r.scale_y = 1.5
    r.separator()
    r.operator("chordsong.load_config", text="Load Config", icon="FILE_FOLDER")
    r.scale_y = 1.5
    r.separator()
    r.scale_y = 1.5
    r.operator("chordsong.append_config", text="Append Config", icon="APPEND_BLEND")
    r.separator()
    r.scale_y = 1.5
    r.operator("chordsong.load_default", text="Load Default Config", icon="LOOP_BACK")
    r.separator()
    r.scale_y = 1.5
    r.operator("chordsong.load_autosave", text="Restore Autosave", icon="RECOVER_LAST")

    box.separator()
