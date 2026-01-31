"""Statistics tab layout for addon preferences."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

STATS_LIST_ROWS = 12


def draw_statistics_tab(prefs, _context, layout):
    """Draw the statistics tab."""
    # Populate the list from current in-memory stats whenever the tab is drawn,
    # so the UI always shows what is being tracked (including after Export).
    if prefs.enable_stats:
        try:
            from ...operators.stats_operators import _refresh_stats_ui
            _refresh_stats_ui(prefs, export_to_file=False)
        except Exception:
            pass

    # Enable/disable statistics tracking
    box = layout.box()
    row = box.row()
    row.alignment = 'CENTER'
    row.label(text="  S T A T I S T I C S ")
    
    row = box.row()
    row.scale_y = 1.5
    row.prop(prefs, "enable_stats", text="Enable Usage Tracking")
    
    if prefs.enable_stats:
        row = box.row()
        row.label(text="Status: Logging active", icon='REC')
    else:
        row = box.row()
        row.label(text="Status: Logging paused", icon='PAUSE')
    
    row = box.row()
    row.label(text="Tracks operator and chord usage to identify workflow patterns.", icon='INFO')
    
    
    # Export section
    box = layout.box()
    row = box.row()
    row.alignment = 'CENTER'
    row.label(text="  E X P O R T ")
    
    row = box.row()
    row.prop(prefs, "stats_export_path", text="Export Path")
    row = box.row()
    row.prop(prefs, "stats_sort_by_usage", text="Sort by Usage", toggle=True)
    row.operator("chordsong.stats_reload", text="Reload from JSON", icon='FILE_REFRESH')
    
    row = box.row()
    row.scale_y = 1.3
    row.operator("chordsong.stats_export", text="Export Stats", icon='EXPORT')

    # Blacklist editor button
    op = row.operator("chordsong.stats_blacklist", text="Edit Blacklist", icon='PREFERENCES')
    op.action = 'EDIT'

    # Auto-export interval setting
    row.prop(prefs, "stats_auto_export_interval", text="Auto Export Interval (seconds)")
    if prefs.stats_auto_export_interval == 0:
        row = box.row()
        row.label(text="Auto-export is disabled. Data will only be saved on manual export.", icon='INFO')


    # UIList for displaying statistics
    row = box.row()
    row.template_list(
        "CHORDSONG_UL_Stats",
        "",
        prefs,
        "stats_collection",
        prefs,
        "stats_collection_index",
        rows=STATS_LIST_ROWS,
    )

    # Display count and blacklist hint
    row = box.row()
    total_items = len(prefs.stats_collection)
    if total_items > 0:
        total_count = sum(item.count for item in prefs.stats_collection)
        row.label(text=f"Total: {total_items} items, {total_count} uses")
        # Show how many are hidden by blacklist so user knows why list can be shorter than JSON
        try:
            from ...core.stats_manager import ChordSong_StatsManager
            ops_count = len(ChordSong_StatsManager.get_stats("operators"))
            chords_count = len(ChordSong_StatsManager.get_stats("chords"))
            total_in_data = ops_count + chords_count
            if total_in_data > total_items:
                row = box.row()
                row.label(text=f"({total_in_data - total_items} hidden by blacklist)", icon='FILTER')
        except Exception:
            pass
    else:
        row.label(text="No statistics data yet. Use Blender to start tracking!")

