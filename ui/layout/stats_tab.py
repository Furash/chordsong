"""Statistics tab layout for addon preferences."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import bpy


# Track if we've done initial refresh to avoid repeated timer registration
_stats_initial_refresh_done = False

def draw_statistics_tab(prefs, _context, layout):
    """Draw the statistics tab."""
    global _stats_initial_refresh_done
    
    # Auto-refresh statistics on first view of tab (only if realtime refresh is disabled)
    if not _stats_initial_refresh_done:
        def refresh_delayed():
            try:
                # Only do initial refresh if realtime refresh is disabled
                if not getattr(prefs, 'stats_realtime_refresh', True):
                    bpy.ops.chordsong.stats_refresh()
            except Exception:
                pass
            return None
        bpy.app.timers.register(refresh_delayed, first_interval=0.01)
        _stats_initial_refresh_done = True
    
    # Enable/disable statistics tracking
    box = layout.box()
    row = box.row()
    row.alignment = 'CENTER'
    row.label(text="  S T A T I S T I C S ")
    
    row = box.row()
    row.scale_y = 1.5
    row.prop(prefs, "enable_stats", text="Enable Usage Tracking")
    
    if prefs.enable_stats:
        # Property tracking toggle
        row = box.row()
        row.label(text="Status: Logging active", icon='REC')
        row = box.row()
        row.scale_y = 1.5
        row.prop(prefs, "stats_track_properties", text="Track Properties (INFO Panel)", toggle=True, icon='INFO')
        if prefs.stats_track_properties:
            row = box.row()
            row.alert = True
            row.label(text="Warning: Requires INFO panel to be open.", icon='ERROR')
            row = box.row()
            row.alert = True
            row.label(text="Warning: Clipboard may be overwritten.", icon='ERROR')
            row = box.row()
            row.label(text="Note: Open INFO panel (Window > Toggle System Console) and minimize it for clarity.", icon='INFO')
        
    else:
        row = box.row()
        row.label(text="Status: Logging paused", icon='PAUSE')
    
    row = box.row()
    row.label(text="Tracks operator, chord, and property usage to identify workflow patterns.", icon='INFO')
    
    # Auto-export interval setting
    row = box.row()
    row.prop(prefs, "stats_auto_export_interval", text="Auto Export Interval (seconds)")
    if prefs.stats_auto_export_interval > 0:
        minutes = prefs.stats_auto_export_interval / 60.0
        if minutes >= 1.0:
            row = box.row()
            row.label(text=f"Data is automatically saved every {minutes:.1f} minute{'s' if minutes != 1.0 else ''} (when new data is recorded).", icon='TIME')
        else:
            row = box.row()
            row.label(text=f"Data is automatically saved every {prefs.stats_auto_export_interval} second{'s' if prefs.stats_auto_export_interval != 1 else ''} (when new data is recorded).", icon='TIME')
    else:
        row = box.row()
        row.label(text="Auto-export is disabled. Data will only be saved on manual export.", icon='INFO')
    
    # # Statistics display
    # box = layout.box()
    # row = box.row()
    # row.alignment = 'CENTER'
    # row.label(text="  S T A T I S T I C S   T A B L E ")
    
    # Sort option and controls
    row = box.row(align=True)
    row.prop(prefs, "stats_sort_by_usage", text="Sort by Usage", toggle=True)
    row.prop(prefs, "stats_realtime_refresh", text="Realtime Refresh", toggle=True, icon='FILE_REFRESH')
    row.operator("chordsong.stats_clear", text="Clear All", icon='TRASH')
    
    # UIList for displaying statistics
    row = box.row()
    row.template_list(
        "CHORDSONG_UL_Stats",
        "",
        prefs,
        "stats_collection",
        prefs,
        "stats_collection_index",
        rows=12,
    )
    
    
    # Display count
    row = box.row()
    total_items = len(prefs.stats_collection)
    if total_items > 0:
        total_count = sum(item.count for item in prefs.stats_collection)
        row.label(text=f"Total: {total_items} items, {total_count} uses")
    else:
        row.label(text="No statistics data yet. Use Blender to start tracking!")

    # Blacklist editor button
    row = box.row(align=True)
    op = row.operator("chordsong.stats_blacklist", text="Edit Blacklist", icon='PREFERENCES')
    op.action = 'EDIT'

    # Export section
    box = layout.box()
    row = box.row()
    row.alignment = 'CENTER'
    row.label(text="  E X P O R T ")
    
    row = box.row()
    row.prop(prefs, "stats_export_path", text="Export Path")
    
    row = box.row()
    row.scale_y = 1.3
    row.operator("chordsong.stats_export", text="Export to JSON", icon='EXPORT')
