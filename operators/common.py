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
    "detect_editor_context",
    "current_script_contexts",
]


def detect_editor_context(context: bpy.types.Context) -> str:
    """Detect the current editor context as a mapping-context token."""
    space = context.space_data
    if space:
        space_type = space.type
        if space_type == 'VIEW_3D':
            if context.mode and context.mode.startswith('EDIT'):
                return "VIEW_3D_EDIT"
            return "VIEW_3D"
        elif space_type == 'IMAGE_EDITOR':
            return "IMAGE_EDITOR"
        elif space_type == 'NODE_EDITOR':
            if hasattr(space, 'tree_type'):
                if space.tree_type == 'GeometryNodeTree':
                    return "GEOMETRY_NODE"
                elif space.tree_type == 'ShaderNodeTree':
                    return "SHADER_EDITOR"
            # Default to shader editor for other node editors
            return "SHADER_EDITOR"
    # Default to 3D View if we can't detect
    return "VIEW_3D"


def current_script_contexts(context: bpy.types.Context) -> set:
    """Context tokens matching the live editor, for scripts-folder scoping."""
    from ..core.script_scanner import script_contexts_for
    space = context.space_data
    space_type = getattr(space, "type", "") if space else ""
    tree_type = getattr(space, "tree_type", None) if space else None
    mode = getattr(context, "mode", "") or ""
    return script_contexts_for(space_type, tree_type, mode)


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


