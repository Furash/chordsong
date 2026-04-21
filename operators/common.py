import bpy

# Re-export get_str_attr and collect_toggle_paths from core for backward compatibility
from ..core.engine import get_str_attr, collect_toggle_paths
from ..utils.addon_package import addon_root_package

__all__ = [
    "prefs",
    "schedule_autosave_safe",
    "get_str_attr",
    "event_in_invoke_region",
    "collect_toggle_paths",
]

def prefs(context: bpy.types.Context):
    """Get addon preferences for extension workflow."""
    package_name = addon_root_package(__package__)
    return context.preferences.addons[package_name].preferences

def schedule_autosave_safe(prefs, delay_s=5.0):
    """Schedule autosave with exception handling. Safe to call anywhere."""
    try:
        from ..core.autosave import schedule_autosave
        schedule_autosave(prefs, delay_s)
    except Exception:  # pylint: disable=broad-exception-caught
        pass


def event_in_invoke_region(context, invoke_area_ptr, invoke_region):
    # event.mouse_region_x/y are relative to whatever region is under the cursor,
    # not the invoke region. Overlay hit-boxes live in the invoke region's coord
    # space — accept clicks only when the event actually fired there.
    if invoke_area_ptr is None or context.area is None:
        return False
    try:
        if context.area.as_pointer() != invoke_area_ptr:
            return False
    except (AttributeError, ReferenceError, RuntimeError):
        return False
    if invoke_region is None or context.region is None:
        return False
    try:
        if context.region.as_pointer() != invoke_region.as_pointer():
            return False
    except (AttributeError, ReferenceError, RuntimeError):
        return False
    return True


