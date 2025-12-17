import bpy

# Re-export get_str_attr from core.engine for backward compatibility
from ..core.engine import get_str_attr

__all__ = ["prefs", "schedule_autosave_safe", "get_str_attr"]


def prefs(context: bpy.types.Context):
    return context.preferences.addons[__package__.split(".")[0]].preferences


def schedule_autosave_safe(prefs, delay_s=5.0):
    """Schedule autosave with exception handling. Safe to call anywhere."""
    try:
        from ..core.autosave import schedule_autosave
        schedule_autosave(prefs, delay_s)
    except Exception:
        pass


