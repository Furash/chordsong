"""Fading confirmation overlay.

Extracted from operators/leader.py to shrink that god-module and keep
fading-overlay state and lifecycle in one place. Used by both the Leader
operator and the keyboard/click execution paths to flash a short-lived
"X fired" confirmation after a chord completes.

Public surface:
    - _show_fading_overlay(context, chord_tokens, label, icon, show_chord=True)
    - _cleanup_fading_overlay()
    - _is_reloading()  — also re-used by leader.py/scripts_overlay for the same
      "addon hot-reload in progress" guard; owned here because the fading
      draw callback is the most sensitive consumer.
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
import bpy  # type: ignore

from ..core.engine import humanize_chord
from ..ui.overlay import draw_fading_overlay
from ..utils.redraw import tag_redraw_all_areas
from .common import prefs


def _is_reloading():
    """True while blinker hot-reload is mid-swap — consumers should bail
    from draw callbacks until the reload completes."""
    return bpy.app.driver_namespace.get("_blinker_reloading", False)


# Module-level state for the fading overlay draw handler. There's only ever
# one fading overlay active at a time — a second _show call cleans the
# first up (see _cleanup_fading_overlay) before installing its own.
_fading_overlay_state = {
    "active": False,
    "chord_text": "",
    "label": "",
    "icon": "",
    "start_time": 0,
    "show_chord": True,
    "draw_handles": {},
    "area": None,
    "invoke_area_ptr": None,
}


def _show_fading_overlay(_context, chord_tokens, label, icon, show_chord=True):
    """Start a fading confirmation overlay for the executed chord.

    Args:
        _context: Blender context (used only for area pointer capture;
            fading is drawn via a background timer, not this context).
        chord_tokens: token list to render in the chord column.
        label: main label text.
        icon: icon character.
        show_chord: when False, skip the chord column (used when the chord
            is internal / not user-triggered).
    """
    state = _fading_overlay_state
    _cleanup_fading_overlay()

    state["active"] = True
    state["chord_text"] = humanize_chord(chord_tokens)
    state["label"] = label
    state["icon"] = icon
    state["show_chord"] = show_chord
    state["start_time"] = time.time()
    try:
        state["invoke_area_ptr"] = (
            _context.area.as_pointer() if (_context and _context.area) else None
        )
    except Exception:
        state["invoke_area_ptr"] = None
    state["area"] = None

    # Pick a space-type class for registering the draw handler so the fading
    # overlay only draws in the editor where it was invoked. Fall back to
    # SpaceView3D for PREFERENCES and other non-editor contexts — the
    # invoke_area_ptr check in the draw callback prevents mis-draws.
    space = None
    try:
        if _context:
            space = getattr(_context, 'space_data', None)
    except Exception:
        pass

    if space:
        try:
            space_type = getattr(space, 'type', None)
            if space_type == 'NODE_EDITOR':
                space_type_class = bpy.types.SpaceNodeEditor
            elif space_type == 'IMAGE_EDITOR':
                space_type_class = bpy.types.SpaceImageEditor
            elif space_type == 'SEQUENCE_EDITOR':
                space_type_class = bpy.types.SpaceSequenceEditor
            elif space_type == 'VIEW_3D':
                space_type_class = bpy.types.SpaceView3D
            else:
                space_type_class = bpy.types.SpaceView3D
        except Exception:
            space_type_class = bpy.types.SpaceView3D
    else:
        space_type_class = bpy.types.SpaceView3D

    if not space_type_class:
        return

    def draw_callback():
        try:
            if _is_reloading():
                return
            if not state["active"]:
                return

            # Find the originally-invoked area (may be in a different window
            # than bpy.context.area, e.g. after the user moved focus).
            target_area = None
            if state["invoke_area_ptr"] is not None:
                try:
                    for window in bpy.context.window_manager.windows:
                        try:
                            screen = window.screen
                            if not screen:
                                continue
                            for area in screen.areas:
                                try:
                                    if area.as_pointer() == state["invoke_area_ptr"]:
                                        target_area = area
                                        break
                                except Exception:
                                    pass
                            if target_area:
                                break
                        except Exception:
                            pass
                except Exception:
                    pass

            if not target_area and state["invoke_area_ptr"] is not None:
                try:
                    if bpy.context.area and bpy.context.area.as_pointer() == state["invoke_area_ptr"]:
                        target_area = bpy.context.area
                except Exception:
                    pass

            if state["invoke_area_ptr"] is not None and not target_area:
                # Prevent mis-draws in non-invoke areas.
                return

            if target_area:
                try:
                    # Pick the biggest region (likely the main WINDOW region)
                    # to avoid drawing into small toolbars/panels.
                    target_region = None
                    max_area = 0
                    for region in target_area.regions:
                        try:
                            w = region.width
                            h = region.height
                            a = w * h
                            if a > max_area:
                                max_area = a
                                target_region = region
                        except Exception:
                            continue

                    if target_region:
                        with bpy.context.temp_override(area=target_area, region=target_region):
                            try:
                                p = prefs(bpy.context)
                            except (KeyError, AttributeError):
                                return
                            if not p:
                                return
                            still_active = draw_fading_overlay(
                                bpy.context, p,
                                state["chord_text"],
                                state["label"],
                                state["icon"],
                                state["start_time"],
                                show_chord=state.get("show_chord", True),
                            )
                            if not still_active:
                                _cleanup_fading_overlay()
                            return
                except Exception:
                    # If temp_override fails, fall through to default context.
                    pass

            # Fallback: current context.
            try:
                p = prefs(bpy.context)
            except (KeyError, AttributeError):
                return
            if not p:
                return
            still_active = draw_fading_overlay(
                bpy.context, p,
                state["chord_text"],
                state["label"],
                state["icon"],
                state["start_time"],
                show_chord=state.get("show_chord", True),
            )
            if not still_active:
                _cleanup_fading_overlay()
        except Exception:
            _cleanup_fading_overlay()

    state["draw_handles"] = {}
    handle = space_type_class.draw_handler_add(draw_callback, (), "WINDOW", "POST_PIXEL")
    state["draw_handles"][space_type_class] = handle

    def tag_target_view():
        stored_area = state.get("area")
        if stored_area:
            try:
                stored_area.tag_redraw()
            except Exception:
                state["area"] = None
                tag_redraw_all_areas()
        else:
            tag_redraw_all_areas()

    tag_target_view()

    def redraw_timer():
        if state["active"]:
            tag_target_view()
            return 0.03  # ~30 FPS redraw during fade
        return None

    bpy.app.timers.register(redraw_timer, first_interval=0.01)


def _cleanup_fading_overlay():
    """Remove the fading-overlay draw handler and reset state."""
    state = _fading_overlay_state
    state["active"] = False
    state["invoke_area_ptr"] = None

    if state["draw_handles"]:
        for st, handle in state["draw_handles"].items():
            try:
                st.draw_handler_remove(handle, "WINDOW")
            except Exception:
                pass
        state["draw_handles"] = {}

    if state["area"]:
        try:
            state["area"].tag_redraw()
        except Exception:
            pass
