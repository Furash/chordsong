"""Statistics tab layout for addon preferences."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

STATS_LIST_ROWS = 12


def draw_stats_tab(prefs, _context, layout):
    """Draw the statistics tab."""
    try:
        from ...core.stats_manager import stats_supported
        if not stats_supported():
            layout.box().label(text="Statistics requires Blender 5.2 or newer.", icon='ERROR')
            return
    except Exception:
        pass

    # Rebuild the list from current counts on every draw so the UI always
    # reflects what is being tracked.
    if prefs.enable_stats:
        try:
            from ...operators.stats_operators import refresh_stats_ui
            refresh_stats_ui(prefs)
        except Exception:
            pass

    box = layout.box()
    row = box.row()
    row.scale_y = 1.5
    row.prop(prefs, "enable_stats", text="Enable Usage Tracking")

    row = box.row()
    if prefs.enable_stats:
        row.label(text="Status: Logging active", icon='REC')
    else:
        row.label(text="Status: Logging paused", icon='PAUSE')
    box.row().label(
        text="Tracks operator and chord usage to identify workflow patterns. Data stays local.",
        icon='INFO',
    )

    try:
        from ...core.stats_manager import reports_available
        if prefs.enable_stats and not reports_available():
            box.row().label(
                text="This Blender version has no wm.reports API — only chords are tracked.",
                icon='ERROR',
            )
    except Exception:
        pass

    # Export / file section
    box = layout.box()
    box.row().prop(prefs, "stats_export_path", text="Stats File")
    row = box.row()
    row.prop(prefs, "stats_sort_by_usage", text="Sort by Usage", toggle=True)
    row.prop(prefs, "stats_auto_export_interval", text="Auto Save Interval (s)")
    if prefs.stats_auto_export_interval == 0:
        box.row().label(text="Auto-save disabled — data is only saved on manual export.", icon='INFO')

    row = box.row()
    row.scale_y = 1.3
    row.operator("chordsong.stats_export", text="Export Stats", icon='EXPORT')
    row.operator("chordsong.stats_reload", text="Reload from JSON", icon='FILE_REFRESH')
    op = row.operator("chordsong.stats_blacklist", text="Edit Blacklist", icon='PREFERENCES')
    op.action = 'EDIT'
    row.operator("chordsong.stats_reset", text="", icon='TRASH')

    # Statistics list
    box.row().template_list(
        "CHORDSONG_UL_Stats",
        "",
        prefs,
        "stats_collection",
        prefs,
        "stats_collection_index",
        rows=STATS_LIST_ROWS,
    )

    row = box.row()
    total_items = len(prefs.stats_collection)
    if total_items > 0:
        total_count = sum(item.count for item in prefs.stats_collection)
        row.label(text=f"Total: {total_items} items, {total_count} uses")
        try:
            from ...core import stats_manager, stats_store
            total_in_data = sum(
                len(stats_manager.get_stats(cat)) for cat in stats_store.CATEGORIES
            )
            if total_in_data > total_items:
                box.row().label(
                    text=f"({total_in_data - total_items} hidden by blacklist)", icon='FILTER'
                )
        except Exception:
            pass
    else:
        row.label(text="No statistics data yet. Use Blender to start tracking!")
