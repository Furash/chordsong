"""Redraw helpers.

`tag_redraw_all_areas` consolidates the "walk every window.screen.area and
call tag_redraw()" loop that appeared in ~6 places across operators/.
Each copy wrapped the inner calls in try/except to tolerate partially-
destroyed bpy areas; this module does the same once, centrally.
"""


def tag_redraw_all_areas(context=None):
    """Tag every area in every window for redraw. Best-effort — any area,
    screen, or window that has been freed at the C level silently skips.

    Pass a context when you have one (slightly faster than importing bpy
    at call time); with context=None we fall back to bpy.context.
    """
    if context is None:
        import bpy  # type: ignore
        wm = bpy.context.window_manager
    else:
        wm = context.window_manager
    try:
        for window in wm.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    try:
                        area.tag_redraw()
                    except Exception:  # pylint: disable=broad-exception-caught
                        # Area is partially destroyed; skip.
                        pass
            except Exception:  # pylint: disable=broad-exception-caught
                # Window or screen is invalid.
                pass
    except Exception:  # pylint: disable=broad-exception-caught
        # Best effort: never crash Blender from a redraw helper.
        pass
