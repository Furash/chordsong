import bpy


def prefs(context: bpy.types.Context):
    return context.preferences.addons[__package__.split(".")[0]].preferences


def schedule_autosave_safe(prefs, delay_s=5.0):
    """Schedule autosave with exception handling. Safe to call anywhere."""
    try:
        from ..core.autosave import schedule_autosave
        schedule_autosave(prefs, delay_s)
    except Exception:
        pass


def get_str_attr(obj, attr, default=""):
    """Get string attribute with fallback and strip whitespace."""
    return (getattr(obj, attr, default) or default).strip()


