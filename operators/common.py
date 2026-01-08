import bpy

# Re-export get_str_attr from core.engine for backward compatibility
from ..core.engine import get_str_attr
from ..utils.addon_package import addon_root_package

__all__ = ["prefs", "schedule_autosave_safe", "get_str_attr"]

def prefs(context: bpy.types.Context):
    """Get addon preferences for extension workflow."""
    package_name = addon_root_package(__package__)
    return context.preferences.addons[package_name].preferences

def schedule_autosave_safe(prefs, delay_s=5.0):
    """Schedule autosave with exception handling. Safe to call anywhere."""
    try:
        from ..core.autosave import schedule_autosave
        schedule_autosave(prefs, delay_s)
    except Exception:
        pass
