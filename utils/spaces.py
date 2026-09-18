"""bpy-side helpers over the editor-context registry (core.contexts).

Overlay operators (Leader, Search, Scripts) register one draw handler per
supported space class so the overlay stays visible whichever editor the
modal was invoked from. This module owns that fan-out so the space list
lives in exactly one place.
"""
import bpy

from ..core.contexts import (
    DEFAULT_CONTEXT,
    SPACE_CLASS_NAMES,
    SUPPORTED_SPACE_TYPES,
    overlay_regions_for,
)

__all__ = [
    "SUPPORTED_SPACE_TYPES",
    "space_class_for",
    "add_overlay_handlers",
    "remove_overlay_handlers",
]


def space_class_for(space_type, fallback=True):
    """bpy.types Space subclass for a space type, or SpaceView3D when the
    type is unknown and ``fallback`` is set (None otherwise)."""
    name = SPACE_CLASS_NAMES.get(space_type or "")
    cls = getattr(bpy.types, name, None) if name else None
    if cls is None and fallback:
        cls = getattr(bpy.types, SPACE_CLASS_NAMES[DEFAULT_CONTEXT], None)
    return cls


def add_overlay_handlers(callback, args=(), draw_type="POST_PIXEL"):
    """Register ``callback`` on every supported space/region pair.

    Returns a list of (space_class, region_type, handle) triples to hand
    back to remove_overlay_handlers. Space classes missing from this
    Blender build are skipped silently.
    """
    handles = []
    for space_type, class_name in SPACE_CLASS_NAMES.items():
        cls = getattr(bpy.types, class_name, None)
        if cls is None:
            continue
        for region_type in overlay_regions_for(space_type):
            try:
                handle = cls.draw_handler_add(callback, tuple(args), region_type, draw_type)
            except Exception:  # pylint: disable=broad-exception-caught
                continue
            handles.append((cls, region_type, handle))
    return handles


def remove_overlay_handlers(handles):
    """Remove handlers registered by add_overlay_handlers. Best-effort."""
    for cls, region_type, handle in list(handles) if handles else []:
        try:
            cls.draw_handler_remove(handle, region_type)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
