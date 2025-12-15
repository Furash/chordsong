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

# Global state for last executed chord (for repeat functionality)
_last_chord_state = {
    "mapping_type": None,
    "operator": None,
    "kwargs": None,
    "call_context": None,
    "python_file": None,
    "label": None,
    "icon": None,
    "chord_tokens": None,
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
    
    # Helper function to tag all 3D views for redraw
    def tag_all_views():
        try:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.tag_redraw()
        except Exception:
            # Fallback: try the stored area
            if state["area"]:
                try:
                    state["area"].tag_redraw()
                except Exception:
                    pass
    
    # Immediately tag for redraw
    tag_all_views()
    
    # Set up a timer to periodically redraw while fading
    def redraw_timer():
        if state["active"]:
            tag_all_views()
            return 0.03  # Redraw every 30ms for smooth fade
        return None
    
    # Register timer with immediate first redraw
    bpy.app.timers.register(redraw_timer, first_interval=0.0)


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
    
    # Tag all 3D views for redraw to clear the overlay
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
    except Exception:
        # Fallback: try the stored area
        if state["area"]:
            try:
                state["area"].tag_redraw()
            except Exception:
                pass


def cleanup_all_handlers():
    """Clean up all draw handlers and timers. Called on addon unregister."""
    _cleanup_fading_overlay()
    # Reset last chord state
    _last_chord_state["mapping_type"] = None
    _last_chord_state["operator"] = None
    _last_chord_state["kwargs"] = None
    _last_chord_state["call_context"] = None
    _last_chord_state["python_file"] = None
    _last_chord_state["label"] = None
    _last_chord_state["icon"] = None
    _last_chord_state["chord_tokens"] = None


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

    def _finish(self, context: bpy.types.Context):  # pylint: disable=unused-argument
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):  # pylint: disable=unused-argument
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

        # Check for <leader><leader> (repeat last chord)
        # Leader key is SPACE - if buffer is empty and user presses SPACE, repeat last
        if not self._buffer and event.type == "SPACE":
            last = _last_chord_state
            if last["mapping_type"] == "PYTHON_FILE" and last["python_file"]:
                # Repeat last Python script
                python_file = last["python_file"]
                label = last["label"] or "(repeat)"
                icon = last["icon"] or ""
                chord_tokens = last["chord_tokens"] or ["space", "space"]
                
                # Capture viewport context before finishing
                ctx_viewport = {}
                for key in ("area", "region", "space_data", "window", "screen"):
                    val = getattr(context, key, None)
                    if val is not None:
                        ctx_viewport[key] = val
                
                self._finish(context)
                
                def execute_script_repeat_delayed():
                    try:
                        import os
                        if not os.path.exists(python_file):
                            print(f"Chord Song: Script file not found: {python_file}")
                            return None
                        
                        with open(python_file, 'r', encoding='utf-8') as f:
                            script_text = f.read()
                        
                        # Execute with captured context
                        if ctx_viewport:
                            with bpy.context.temp_override(**ctx_viewport):
                                exec(compile(script_text, python_file, 'exec'))  # pylint: disable=exec-used
                        else:
                            exec(compile(script_text, python_file, 'exec'))  # pylint: disable=exec-used
                        
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        
                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to repeat script {python_file}: {e}")
                        traceback.print_exc()
                    return None
                
                bpy.app.timers.register(execute_script_repeat_delayed, first_interval=0.01)
                return {"FINISHED"}
                
            elif last["operator"]:
                # Repeat the last operator chord
                op = last["operator"]
                kwargs = last["kwargs"] or {}
                call_ctx = last["call_context"] or "EXEC_DEFAULT"
                label = last["label"] or "(repeat)"
                icon = last["icon"] or ""
                chord_tokens = last["chord_tokens"] or ["space", "space"]

                # Capture viewport context before finishing (safe in modal method)
                ctx_viewport = {}
                for key in ("area", "region", "space_data", "window", "screen"):
                    val = getattr(context, key, None)
                    if val is not None:
                        ctx_viewport[key] = val

                self._finish(context)

                def execute_repeat_delayed():
                    result_set = set()
                    try:
                        mod_name, fn_name = op.split(".", 1)
                        opmod = getattr(bpy.ops, mod_name)
                        opfn = getattr(opmod, fn_name)

                        # Execute with captured context (captured in modal, used in timer)
                        if call_ctx == "INVOKE_DEFAULT":
                            if ctx_viewport:
                                with bpy.context.temp_override(**ctx_viewport):
                                    result_set = opfn('INVOKE_DEFAULT', **kwargs)
                            else:
                                result_set = opfn('INVOKE_DEFAULT', **kwargs)
                        else:
                            if ctx_viewport:
                                with bpy.context.temp_override(**ctx_viewport):
                                    result_set = opfn('EXEC_DEFAULT', **kwargs)
                            else:
                                result_set = opfn('EXEC_DEFAULT', **kwargs)

                        if result_set and 'FINISHED' in result_set:
                            _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        elif result_set and 'CANCELLED' not in result_set:
                            _show_fading_overlay(bpy.context, chord_tokens, label, icon)

                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to repeat operator {op}: {e}")
                        traceback.print_exc()
                    return None

                bpy.app.timers.register(execute_repeat_delayed, first_interval=0.01)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, "No previous chord to repeat")
                self._finish(context)
                return {"CANCELLED"}

        self._buffer.append(tok)
        self._scroll_offset = 0  # Reset scroll when adding to buffer

        # Exact match?
        m = find_exact_mapping(p.mappings, self._buffer)
        if m:
            mapping_type = getattr(m, "mapping_type", "OPERATOR")
            
            # Get label and icon for fading overlay
            label = getattr(m, "label", "") or "(no label)"
            icon = getattr(m, "icon", "") or ""
            
            # Capture the buffer before finishing
            chord_tokens = list(self._buffer)
            
            # Handle Python script execution
            if mapping_type == "PYTHON_FILE":
                python_file = (getattr(m, "python_file", "") or "").strip()
                if not python_file:
                    self.report({"WARNING"}, f'Chord "{" ".join(self._buffer)}" has no script file')
                    self._finish(context)
                    return {"CANCELLED"}
                
                # Capture viewport context BEFORE finishing modal (when we have valid context)
                ctx_viewport = {}
                for key in ("area", "region", "space_data", "window", "screen"):
                    val = getattr(context, key, None)
                    if val is not None:
                        ctx_viewport[key] = val
                
                # Finish modal before executing script
                self._finish(context)
                
                # Execute Python script
                def execute_script_delayed():
                    try:
                        import os
                        if not os.path.exists(python_file):
                            print(f"Chord Song: Script file not found: {python_file}")
                            return None
                        
                        # Read and execute the script
                        with open(python_file, 'r', encoding='utf-8') as f:
                            script_text = f.read()
                        
                        # Execute in Blender's context with captured viewport context
                        if ctx_viewport:
                            with bpy.context.temp_override(**ctx_viewport):
                                exec(compile(script_text, python_file, 'exec'))  # pylint: disable=exec-used
                        else:
                            exec(compile(script_text, python_file, 'exec'))  # pylint: disable=exec-used
                        
                        # Show fading overlay on success
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        
                        # Store as last chord for repeat functionality
                        _last_chord_state["mapping_type"] = "PYTHON_FILE"
                        _last_chord_state["python_file"] = python_file
                        _last_chord_state["operator"] = None
                        _last_chord_state["kwargs"] = None
                        _last_chord_state["call_context"] = None
                        _last_chord_state["label"] = label
                        _last_chord_state["icon"] = icon
                        _last_chord_state["chord_tokens"] = chord_tokens
                        
                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to execute script {python_file}: {e}")
                        traceback.print_exc()
                    return None
                
                bpy.app.timers.register(execute_script_delayed, first_interval=0.01)
                return {"FINISHED"}
            
            # Handle operator execution
            op = (m.operator or "").strip()
            if not op:
                self.report({"WARNING"}, f'Chord "{" ".join(self._buffer)}" has no operator')
                self._finish(context)
                return {"CANCELLED"}

            kwargs = parse_kwargs(getattr(m, "kwargs_json", "{}"))
            call_ctx = (getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()

            # Capture viewport context BEFORE finishing modal (when we have valid context).
            # This is safe because we're in modal() method, not in a draw handler.
            # We'll use these captured values INSIDE the timer (when we're outside draw phase).
            ctx_viewport = {}
            for key in ("area", "region", "space_data", "window", "screen"):
                val = getattr(context, key, None)
                if val is not None:
                    ctx_viewport[key] = val

            # Finish the modal operator FIRST to ensure clean state before calling other operators.
            # This prevents blocking issues when opening preferences or other UI operations.
            self._finish(context)

            # Defer operator execution to next frame using a timer.
            # The timer ensures we're completely outside the draw/render phase when executing.
            def execute_operator_delayed():
                result_set = set()
                try:
                    mod_name, fn_name = op.split(".", 1)
                    opmod = getattr(bpy.ops, mod_name)
                    opfn = getattr(opmod, fn_name)

                    # Execute operator with captured context override.
                    # Context was captured in modal() method (safe) but used in timer (outside draw).
                    if call_ctx == "INVOKE_DEFAULT":
                        if ctx_viewport:
                            with bpy.context.temp_override(**ctx_viewport):
                                result_set = opfn('INVOKE_DEFAULT', **kwargs)
                        else:
                            result_set = opfn('INVOKE_DEFAULT', **kwargs)
                    else:
                        if ctx_viewport:
                            with bpy.context.temp_override(**ctx_viewport):
                                result_set = opfn('EXEC_DEFAULT', **kwargs)
                        else:
                            result_set = opfn('EXEC_DEFAULT', **kwargs)
                    
                    # Show fading overlay on success
                    if result_set and 'FINISHED' in result_set:
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        # Store as last chord for repeat functionality
                        _last_chord_state["mapping_type"] = "OPERATOR"
                        _last_chord_state["operator"] = op
                        _last_chord_state["kwargs"] = kwargs
                        _last_chord_state["call_context"] = call_ctx
                        _last_chord_state["python_file"] = None
                        _last_chord_state["label"] = label
                        _last_chord_state["icon"] = icon
                        _last_chord_state["chord_tokens"] = chord_tokens
                    elif result_set and 'CANCELLED' not in result_set:
                        # Also show for RUNNING_MODAL or PASS_THROUGH
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        # Store as last chord for repeat functionality
                        _last_chord_state["mapping_type"] = "OPERATOR"
                        _last_chord_state["operator"] = op
                        _last_chord_state["kwargs"] = kwargs
                        _last_chord_state["call_context"] = call_ctx
                        _last_chord_state["python_file"] = None
                        _last_chord_state["label"] = label
                        _last_chord_state["icon"] = icon
                        _last_chord_state["chord_tokens"] = chord_tokens
                    
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


