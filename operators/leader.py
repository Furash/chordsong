"""Leader operator for chord capture with which-key overlay."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
import bpy  # type: ignore

from ..core.engine import candidates_for_prefix, find_exact_mapping, normalize_token, parse_kwargs
from ..ui.overlay import draw_overlay, draw_fading_overlay
from .common import prefs


# Global state for fading overlay
_fading_overlay_state = {
    "active": False,
    "chord_text": "",
    "label": "",
    "icon": "",
    "start_time": 0,
    "draw_handle": None,
    "area": None,
}


def _show_fading_overlay(context, chord_tokens, label, icon):
    """Start showing a fading overlay for the executed chord."""
    state = _fading_overlay_state
    
    # Clean up any existing overlay
    if state["draw_handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(state["draw_handle"], "WINDOW")
        except Exception:
            pass
    
    # Set up new fading overlay
    state["active"] = True
    state["chord_text"] = "+".join(chord_tokens).upper()
    state["label"] = label
    state["icon"] = icon
    state["start_time"] = time.time()
    state["area"] = context.area
    
    # Add draw handler
    def draw_callback():
        try:
            p = prefs(bpy.context)
            still_active = draw_fading_overlay(
                bpy.context, p, 
                state["chord_text"], 
                state["label"], 
                state["icon"], 
                state["start_time"]
            )
            
            if not still_active:
                # Time to remove the overlay
                _cleanup_fading_overlay()
        except Exception:
            _cleanup_fading_overlay()
    
    state["draw_handle"] = bpy.types.SpaceView3D.draw_handler_add(
        draw_callback, (), "WINDOW", "POST_PIXEL"
    )
    
    # Tag for redraw
    if state["area"]:
        try:
            state["area"].tag_redraw()
        except Exception:
            pass
    
    # Set up a timer to periodically redraw while fading
    def redraw_timer():
        if state["active"] and state["area"]:
            try:
                state["area"].tag_redraw()
                return 0.03  # Redraw every 30ms for smooth fade
            except Exception:
                pass
        return None
    
    bpy.app.timers.register(redraw_timer, first_interval=0.03)


def _cleanup_fading_overlay():
    """Clean up the fading overlay."""
    state = _fading_overlay_state
    state["active"] = False
    
    if state["draw_handle"] is not None:
        try:
            bpy.types.SpaceView3D.draw_handler_remove(state["draw_handle"], "WINDOW")
        except Exception:
            pass
        state["draw_handle"] = None
    
    if state["area"]:
        try:
            state["area"].tag_redraw()
        except Exception:
            pass


class CHORDSONG_OT_Leader(bpy.types.Operator):
    """Start chord capture (leader)"""

    bl_idname = "chordsong.leader"
    bl_label = "Chord Song Leader"
    bl_options = {"REGISTER"}

    _draw_handle = None
    _buffer = None
    _region = None
    _area = None
    _scroll_offset = 0

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handle is not None:
            return

        # Best effort: only draw in the region/area we started from.
        self._area = context.area
        self._region = context.region

        self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            self._draw_callback, (context,), "WINDOW", "POST_PIXEL"
        )

    def _remove_draw_handler(self):
        if self._draw_handle is None:
            return
        try:
            bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, "WINDOW")
        except Exception:
            pass
        self._draw_handle = None

    def _tag_redraw(self):
        if self._area:
            try:
                self._area.tag_redraw()
            except Exception:
                pass

    def _draw_callback(self, context: bpy.types.Context):
        """Draw callback for the overlay."""
        p = prefs(context)
        if not p.overlay_enabled:
            return

        # Use the buffer tokens for overlay rendering
        buffer_tokens = self._buffer or []
        draw_overlay(context, p, buffer_tokens)

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start chord capture modal operation."""
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
        self._scroll_offset = 0

        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted.

        Blender calls this when the modal operator is interrupted (area change, file load, etc).
        Ensure we always remove timers/draw handlers so the draw callback can't run after the
        operator's StructRNA has been freed.
        """
        self._finish(context)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        p = prefs(context)

        # Cancel keys
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}

        # Mouse wheel scrolling
        if event.type == "WHEELUPMOUSE":
            self._scroll_offset = max(0, self._scroll_offset - 1)
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        if event.type == "WHEELDOWNMOUSE":
            self._scroll_offset += 1
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # Backspace to go up one level
        if event.type == "BACK_SPACE" and event.value == "PRESS":
            if self._buffer:
                self._buffer.pop()
                self._scroll_offset = 0
                self._tag_redraw()
                return {"RUNNING_MODAL"}
            else:
                # No buffer, treat as cancel
                self._finish(context)
                return {"CANCELLED"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        tok = normalize_token(event.type)
        if tok is None:
            return {"RUNNING_MODAL"}

        self._buffer.append(tok)
        self._scroll_offset = 0  # Reset scroll when adding to buffer

        # Exact match?
        m = find_exact_mapping(p.mappings, self._buffer)
        if m:
            op = (m.operator or "").strip()
            if not op:
                self.report({"WARNING"}, f'Chord "{" ".join(self._buffer)}" has no operator')
                self._finish(context)
                return {"CANCELLED"}

            kwargs = parse_kwargs(getattr(m, "kwargs_json", "{}"))
            call_ctx = (getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()

            # Get label and icon for fading overlay
            label = getattr(m, "label", "") or "(no label)"
            icon = getattr(m, "icon", "") or ""
            
            # Capture the buffer before finishing
            chord_tokens = list(self._buffer)

            # Capture full context for context-sensitive operators (e.g., view3d.view_all)
            # Store the current context as a copy to use later
            ctx = context.copy()

            # Finish the modal operator FIRST to ensure clean state before calling other operators
            # This prevents blocking issues when opening preferences or other UI operations
            self._finish(context)

            # Defer operator execution to next frame using a timer
            # This ensures the modal operator fully finishes before the next operator runs
            def execute_operator_delayed():
                result_set = set()
                try:
                    mod_name, fn_name = op.split(".", 1)
                    opmod = getattr(bpy.ops, mod_name)
                    opfn = getattr(opmod, fn_name)

                    # Execute operator with proper context
                    # For INVOKE_DEFAULT, we need to ensure the operator is called with the right context
                    # For EXEC_DEFAULT, we can call it directly
                    
                    if call_ctx == "INVOKE_DEFAULT":
                        # For invoke context, use temp_override to provide the right area/region
                        with bpy.context.temp_override(**ctx):
                            result_set = opfn('INVOKE_DEFAULT', **kwargs)
                    else:
                        # For exec context, call directly with temp_override
                        # This ensures proper integration with undo/redo and operator repeat
                        with bpy.context.temp_override(**ctx):
                            result_set = opfn('EXEC_DEFAULT', **kwargs)
                    
                    # Show fading overlay on success
                    if result_set and 'FINISHED' in result_set:
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                    elif result_set and 'CANCELLED' not in result_set:
                        # Also show for RUNNING_MODAL or PASS_THROUGH
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                    
                except Exception as e:
                    # Log error for debugging
                    import traceback
                    print(f"Chord Song: Failed to execute operator {op}: {e}")
                    traceback.print_exc()
                return None  # Run once

            bpy.app.timers.register(execute_operator_delayed, first_interval=0.01)
            return {"FINISHED"}

        # Still a prefix?
        cands = candidates_for_prefix(p.mappings, self._buffer)
        if cands:
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # No match
        self.report({"WARNING"}, f'Unknown chord: "{" ".join(self._buffer)}"')
        self._finish(context)
        return {"CANCELLED"}


