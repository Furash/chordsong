"""
Addon Preferences UI layout entry point.
"""

from .config import draw_config_section
from .ui_tab import draw_ui_tab
from .mappings_tab import draw_mappings_tab

def draw_addon_preferences(prefs, context, layout):
    """Main dispatcher for addon preferences UI."""
    # Ensure defaults are populated
    prefs.ensure_defaults()

    col = layout.column()

    # "Tabs" (simple enum switch)
    col.row(align=True).prop(prefs, "prefs_tab", expand=True)

    # Config box (shown above tabs for easy access)
    draw_config_section(prefs, col)

    # Dispatch to specific tab
    if prefs.prefs_tab == "UI":
        draw_ui_tab(prefs, col)
    else:
        draw_mappings_tab(prefs, context, col)
