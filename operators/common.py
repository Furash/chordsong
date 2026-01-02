import bpy

# Re-export get_str_attr from core.engine for backward compatibility
from ..core.engine import get_str_attr

__all__ = ["prefs", "schedule_autosave_safe", "get_str_attr"]

def prefs(context: bpy.types.Context):
    """Get addon preferences for extension workflow."""
    # Extension format: bl_ext.{repo}.{addon_id}.{submodule...}
    # We need the first 3 parts: bl_ext.repo.addon_id
    pkg = __package__ or "bl_ext.user_default.chordsong"
    parts = pkg.split(".")
    package_name = ".".join(parts[:3])
    return context.preferences.addons[package_name].preferences

def schedule_autosave_safe(prefs, delay_s=5.0):
    """Schedule autosave with exception handling. Safe to call anywhere."""
    try:
        from ..core.autosave import schedule_autosave
        schedule_autosave(prefs, delay_s)
    except Exception:
        pass
