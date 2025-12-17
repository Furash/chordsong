"""Leader operator for chord capture with which-key overlay."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
import bpy  # type: ignore

from ..core.engine import candidates_for_prefix, find_exact_mapping, normalize_token, parse_kwargs, filter_mappings_by_context
from ..core.history import add_to_history
from ..ui.overlay import draw_overlay, draw_fading_overlay
from .common import prefs


def _get_leader_key_type():
    """Get the current leader key type from the addon keymap."""
    try:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            return "SPACE"
        
        km = kc.keymaps.get("3D View")
        if not km:
            return "SPACE"
        
        # Find the leader keymap item
        for kmi in km.keymap_items:
            if kmi.idname == "chordsong.leader":
                return kmi.type
        
        return "SPACE"
    except Exception:
        return "SPACE"


# Global state for fading overlay
_fading_overlay_state = {
    "active": False,
    "chord_text": "",
    "label": "",
    "icon": "",
    "start_time": 0,
    "draw_handle": None,
    "area": None,
    "space_type": None,  # Store the space type for proper cleanup
}

# Note: Last chord tracking removed - now handled by history system (core/history.py)


def _show_fading_overlay(context, chord_tokens, label, icon):
    """Start showing a fading overlay for the executed chord."""
    state = _fading_overlay_state
    
    # Clean up any existing overlay
    if state["draw_handle"] is not None:
        try:
            if state["space_type"]:
                state["space_type"].draw_handler_remove(state["draw_handle"], "WINDOW")
            else:
                bpy.types.SpaceView3D.draw_handler_remove(state["draw_handle"], "WINDOW")
        except Exception:
            pass
    
    # Set up new fading overlay
    state["active"] = True
    state["chord_text"] = "+".join(chord_tokens)
    state["label"] = label
    state["icon"] = icon
    state["start_time"] = time.time()
    state["area"] = context.area
    
    # Determine which space type to use for the draw handler
    space = context.space_data
    if space and space.type == 'NODE_EDITOR':
        state["space_type"] = bpy.types.SpaceNodeEditor
    else:
        state["space_type"] = bpy.types.SpaceView3D
    
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
    
    state["draw_handle"] = state["space_type"].draw_handler_add(
        draw_callback, (), "WINDOW", "POST_PIXEL"
    )
    
    # Helper function to tag all relevant areas for redraw
    def tag_all_views():
        try:
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    # Tag both 3D View and Node Editor areas
                    if area.type in {'VIEW_3D', 'NODE_EDITOR'}:
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
            if state["space_type"]:
                state["space_type"].draw_handler_remove(state["draw_handle"], "WINDOW")
            else:
                bpy.types.SpaceView3D.draw_handler_remove(state["draw_handle"], "WINDOW")
        except Exception:
            pass
        state["draw_handle"] = None
        state["space_type"] = None
    
    # Tag all relevant areas for redraw to clear the overlay
    try:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                # Tag both 3D View and Node Editor areas
                if area.type in {'VIEW_3D', 'NODE_EDITOR'}:
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
    # Note: Last chord tracking removed - now handled by history system


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
    _context_type = None  # Store the detected context type
    _space_type = None  # Store the space type for draw handler

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handle is not None:
            return

        # Best effort: only draw in the region/area we started from.
        self._area = context.area
        self._region = context.region

        # Determine which space type to use for the draw handler
        space = context.space_data
        if space and space.type == 'NODE_EDITOR':
            # For Node Editor (Shader Editor, Geometry Nodes)
            self._space_type = bpy.types.SpaceNodeEditor
        else:
            # Default to 3D View
            self._space_type = bpy.types.SpaceView3D

        self._draw_handle = self._space_type.draw_handler_add(
            self._draw_callback, (context,), "WINDOW", "POST_PIXEL"
        )

    def _remove_draw_handler(self):
        if self._draw_handle is None:
            return
        try:
            if self._space_type:
                self._space_type.draw_handler_remove(self._draw_handle, "WINDOW")
            else:
                # Fallback to SpaceView3D if space_type wasn't set
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, "WINDOW")
        except Exception:
            pass
        self._draw_handle = None
        self._space_type = None

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

        # Filter mappings by context for overlay display
        filtered_mappings = filter_mappings_by_context(p.mappings, self._context_type)
        
        # Use the buffer tokens for overlay rendering with filtered mappings
        buffer_tokens = self._buffer or []
        draw_overlay(context, p, buffer_tokens, filtered_mappings)

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start chord capture modal operation."""
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
        self._scroll_offset = 0
        
        # Detect the current editor context
        self._context_type = self._detect_context(context)

        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}
    
    def _detect_context(self, context: bpy.types.Context) -> str:
        """Detect the current editor context."""
        space = context.space_data
        if space:
            space_type = space.type
            if space_type == 'VIEW_3D':
                return "VIEW_3D"
            elif space_type == 'NODE_EDITOR':
                # Check if it's Geometry Nodes or Shader Editor
                if hasattr(space, 'tree_type'):
                    if space.tree_type == 'GeometryNodeTree':
                        return "GEOMETRY_NODE"
                    elif space.tree_type == 'ShaderNodeTree':
                        return "SHADER_EDITOR"
                # Default to shader editor for other node editors
                return "SHADER_EDITOR"
        # Default to 3D View if we can't detect
        return "VIEW_3D"

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

        # Check if shift is pressed
        shift_pressed = event.shift
        
        tok = normalize_token(event.type, shift=shift_pressed)
        if tok is None:
            return {"RUNNING_MODAL"}

        # Check for <leader><leader>
        # If buffer is empty and user presses the leader key again, show recents
        leader_key = _get_leader_key_type()
        if not self._buffer and event.type == leader_key:
            # Open recents instead of repeat
            self._finish(context)
            try:
                bpy.ops.chordsong.recents('INVOKE_DEFAULT')
            except Exception as e:
                print(f"Chord Song: Failed to open recents: {e}")
            return {"FINISHED"}

        self._buffer.append(tok)
        self._scroll_offset = 0  # Reset scroll when adding to buffer

        # Filter mappings by context
        filtered_mappings = filter_mappings_by_context(p.mappings, self._context_type)

        # Exact match?
        m = find_exact_mapping(filtered_mappings, self._buffer)
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
                        
                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="PYTHON_FILE",
                            python_file=python_file,
                        )
                        
                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to execute script {python_file}: {e}")
                        traceback.print_exc()
                    return None
                
                bpy.app.timers.register(execute_script_delayed, first_interval=0.01)
                return {"FINISHED"}
            
            # Handle context toggle execution
            if mapping_type == "CONTEXT_TOGGLE":
                context_path = (getattr(m, "context_path", "") or "").strip()
                if not context_path:
                    self.report({"ERROR"}, f'Toggle mapping "{" ".join(self._buffer)}" has no context path. Please fix in preferences.')
                    print(f"Chord Song: Toggle mapping '{' '.join(self._buffer)}' is missing context_path property")
                    self._finish(context)
                    return {"CANCELLED"}
                
                # Validate that the context path has at least one part
                if '.' not in context_path:
                    self.report({"ERROR"}, f'Invalid context path "{context_path}" - must include context (e.g., "space_data.overlay.show_stats")')
                    print(f"Chord Song: Invalid context path '{context_path}' for chord '{' '.join(self._buffer)}'")
                    self._finish(context)
                    return {"CANCELLED"}
                
                # Capture viewport context BEFORE finishing modal
                ctx_viewport = {}
                for key in ("area", "region", "space_data", "window", "screen"):
                    val = getattr(context, key, None)
                    if val is not None:
                        ctx_viewport[key] = val
                
                self._finish(context)
                
                def execute_toggle_delayed():
                    try:
                        # Define the toggle function to execute with proper context
                        def do_toggle():
                            # Navigate to the property using the path
                            # e.g., "space_data.overlay.show_stats"
                            parts = context_path.split('.')
                            obj = bpy.context
                            
                            # Navigate to the parent object
                            for i, part in enumerate(parts[:-1]):
                                next_obj = getattr(obj, part, None)
                                if next_obj is None:
                                    current_path = ".".join(parts[:i+1])
                                    print(f"Chord Song: Could not find '{part}' in path '{context_path}'")
                                    print(f"  -> Failed at: {current_path}")
                                    print(f"  -> Available on context: {[attr for attr in dir(obj) if not attr.startswith('_')][:10]}...")
                                    return None
                                obj = next_obj
                            
                            # Get the property name
                            prop_name = parts[-1]
                            
                            # Toggle the boolean value
                            if not hasattr(obj, prop_name):
                                print(f"Chord Song: Could not find property '{prop_name}' in path '{context_path}'")
                                print(f"  -> Object type: {type(obj).__name__}")
                                print(f"  -> Available properties: {[attr for attr in dir(obj) if not attr.startswith('_')][:10]}...")
                                return None
                            
                            current_value = getattr(obj, prop_name)
                            
                            if not isinstance(current_value, bool):
                                print(f"Chord Song: Property '{context_path}' is not a boolean (got {type(current_value).__name__})")
                                return None
                            
                            # Toggle it
                            setattr(obj, prop_name, not current_value)
                            
                            # Return the new state for the overlay message
                            return not current_value
                        
                        # Execute with context override if available
                        if ctx_viewport:
                            with bpy.context.temp_override(**ctx_viewport):
                                new_value = do_toggle()
                        else:
                            new_value = do_toggle()
                        
                        # Show fading overlay
                        if new_value is not None:
                            status = "ON" if new_value else "OFF"
                            _show_fading_overlay(bpy.context, chord_tokens, f"{label} ({status})", icon)
                        
                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="CONTEXT_TOGGLE",
                            context_path=context_path,
                        )
                        
                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to toggle context '{context_path}': {e}")
                        traceback.print_exc()
                    return None
                
                bpy.app.timers.register(execute_toggle_delayed, first_interval=0.01)
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
                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="OPERATOR",
                            operator=op,
                            kwargs=kwargs,
                            call_context=call_ctx,
                        )
                    elif result_set and 'CANCELLED' not in result_set:
                        # Also show for RUNNING_MODAL or PASS_THROUGH
                        _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="OPERATOR",
                            operator=op,
                            kwargs=kwargs,
                            call_context=call_ctx,
                        )
                    
                except Exception as e:
                    # Log error for debugging
                    import traceback
                    print(f"Chord Song: Failed to execute operator {op}: {e}")
                    traceback.print_exc()
                return None  # Run once

            bpy.app.timers.register(execute_operator_delayed, first_interval=0.01)
            return {"FINISHED"}

        # Still a prefix?
        cands = candidates_for_prefix(filtered_mappings, self._buffer)
        if cands:
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # No match
        self.report({"WARNING"}, f'Unknown chord: "{" ".join(self._buffer)}"')
        self._finish(context)
        return {"CANCELLED"}


