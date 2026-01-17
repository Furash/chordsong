"""Leader operator for chord capture with which-key overlay."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
import bpy  # type: ignore

from ..core.engine import (
    candidates_for_prefix,
    find_exact_mapping,
    humanize_chord,
    normalize_token,
    parse_kwargs,
    filter_mappings_by_context,
    get_leader_key_type,
)
from ..core.history import add_to_history
from ..ui.overlay import draw_overlay, draw_fading_overlay
from ..utils.render import capture_viewport_context
from .common import prefs
from .test_overlay import disable_test_overlays

# Global state for fading overlay
_fading_overlay_state = {
    "active": False,
    "chord_text": "",
    "label": "",
    "icon": "",
    "start_time": 0,
    "show_chord": True,  # Whether to display the chord text
    "draw_handles": {},  # Dictionary of space_type -> handle
    "area": None,
    "invoke_area_ptr": None,  # Store area pointer for comparison
}

# Global state for panel visibility (shared between Leader and Recents)
_panel_states_global = {}

def _show_fading_overlay(_context, chord_tokens, label, icon, show_chord=True):
    """Start showing a fading overlay for the executed chord.

    Args:
        _context: Blender context
        chord_tokens: List of chord tokens
        label: Label text to display
        icon: Icon to display
        show_chord: Whether to display the chord text (default True)
    """
    state = _fading_overlay_state

    # Clean up any existing overlay
    _cleanup_fading_overlay()

    # Set up new fading overlay
    state["active"] = True
    state["chord_text"] = humanize_chord(chord_tokens)
    state["label"] = label
    state["icon"] = icon
    state["show_chord"] = show_chord
    state["start_time"] = time.time()
    # Store area pointer for comparison during draw
    # as_pointer() gives us a stable memory address for the area
    try:
        state["invoke_area_ptr"] = _context.area.as_pointer() if (_context and _context.area) else None
    except Exception:
        state["invoke_area_ptr"] = None
    state["area"] = None

    # Determine which space type to use based on the context
    # Only register handler for the specific space type where overlay was invoked
    space = None
    space_type_class = None

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
                # For unsupported space types (like PREFERENCES), fall back to View3D
                # The area pointer check will prevent drawing in wrong areas
                space_type_class = bpy.types.SpaceView3D
        except Exception:
            # If we can't access space.type, fall back to View3D
            space_type_class = bpy.types.SpaceView3D
    else:
        # If there's no space_data (e.g., preferences window), fall back to View3D
        # The area pointer check will ensure we only draw in the correct area
        space_type_class = bpy.types.SpaceView3D

    # If we still don't have a valid space type class, don't register handler
    if not space_type_class:
        return

    def draw_callback():
        try:
            # Check if fading overlay is still active
            if not state["active"]:
                return

            # Find the original area where overlay was invoked
            # Search through all windows/areas to find the one matching invoke_area_ptr
            # This is necessary because bpy.context.area might be different (e.g., preferences window)
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

            # If we couldn't find the target area, check if current context area matches
            if not target_area and state["invoke_area_ptr"] is not None:
                try:
                    if bpy.context.area and bpy.context.area.as_pointer() == state["invoke_area_ptr"]:
                        target_area = bpy.context.area
                except Exception:
                    pass

            # If we still don't have a target area, skip drawing
            # (This prevents showing overlay in wrong areas)
            if state["invoke_area_ptr"] is not None and not target_area:
                return

            # Create a context override for the target area if we found it
            # Otherwise use current context
            if target_area:
                try:
                    # Try to get region from target area (usually the WINDOW region)
                    # Don't access region.type directly - it can crash
                    # Instead, find the largest region by area (width * height) which is typically the main viewport
                    target_region = None
                    max_area = 0
                    for region in target_area.regions:
                        try:
                            # WINDOW regions have width and height, other regions might not
                            # Find the largest region to avoid using small toolbars/panels
                            w = region.width
                            h = region.height
                            area = w * h
                            if area > max_area:
                                max_area = area
                                target_region = region
                        except Exception:
                            continue

                    if target_region:
                        # Create context override with target area and region
                        with bpy.context.temp_override(area=target_area, region=target_region):
                            try:
                                p = prefs(bpy.context)
                            except (KeyError, AttributeError):
                                # Addon is being disabled/unregistered
                                return
                            if not p:
                                return

                            still_active = draw_fading_overlay(
                                bpy.context, p,
                                state["chord_text"],
                                state["label"],
                                state["icon"],
                                state["start_time"],
                                show_chord=state.get("show_chord", True)
                            )

                            if not still_active:
                                _cleanup_fading_overlay()
                            return
                except Exception:
                    # If temp_override fails, fall through to default context
                    pass

            # Fallback: use current context
            try:
                p = prefs(bpy.context)
            except (KeyError, AttributeError):
                # Addon is being disabled/unregistered
                return
            if not p:
                return

            still_active = draw_fading_overlay(
                bpy.context, p,
                state["chord_text"],
                state["label"],
                state["icon"],
                state["start_time"],
                show_chord=state.get("show_chord", True)
            )

            if not still_active:
                _cleanup_fading_overlay()
        except Exception:
            _cleanup_fading_overlay()

    # Only register handler for the specific space type where overlay was invoked
    state["draw_handles"] = {}
    if space_type_class:
        handle = space_type_class.draw_handler_add(draw_callback, (), "WINDOW", "POST_PIXEL")
        state["draw_handles"][space_type_class] = handle

    # Helper function to tag the target area for redraw
    def tag_target_view():
        stored_area = state.get("area")
        if stored_area:
            try:
                # Don't access stored_area.type - it can crash on destroyed areas
                # Just try to tag_redraw directly and catch any exception
                stored_area.tag_redraw()
            except Exception:
                # Area is invalid, clear it and tag all relevant areas
                state["area"] = None
                tag_all_views()
        else:
            # No stored area, tag all relevant areas
            tag_all_views()

    # Helper function to tag all relevant areas for redraw
    def tag_all_views():
        try:
            for window in bpy.context.window_manager.windows:
                try:
                    screen = window.screen
                    if not screen:
                        continue
                    for area in screen.areas:
                        # Don't access area.type - it can crash on destroyed areas
                        # Just try to tag_redraw and catch exceptions
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # Immediately tag for redraw
    tag_target_view()

    # Set up a timer to periodically redraw while fading
    def redraw_timer():
        if state["active"]:
            tag_target_view()
            return 0.03  # Redraw every 30ms for smooth fade
        return None


    # Register timer with immediate first redraw
    bpy.app.timers.register(redraw_timer, first_interval=0.0)

def _cleanup_fading_overlay():
    """Clean up the fading overlay."""
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

    # Tag only the target area for redraw to clear the overlay
    if state["area"]:
        try:
            state["area"].tag_redraw()
        except Exception:
            pass


def cleanup_all_handlers():
    """Clean up all draw handlers and timers. Called on addon unregister."""
    _cleanup_fading_overlay()
    disable_test_overlays()

class CHORDSONG_OT_Leader(bpy.types.Operator):
    """Start chord capture (leader)"""

    bl_idname = "chordsong.leader"
    bl_label = "Chord Song Leader"
    bl_options = {"REGISTER"}

    _draw_handles = {}  # Dictionary of space_type -> handle
    _buffer = None
    _region = None
    _area = None
    _invoke_area_ptr = None  # Store area pointer for comparison
    _scroll_offset = 0
    _context_type = None  # Store the detected context type
    _last_mod_type = None  # Store the type of the last modifier key
    _panel_states = {}  # Store original panel visibility states: {area_ptr: {"n_panel": bool, "t_panel": bool}}
    _ctrl_held = False  # Track modifier keys for multi-toggle feature
    _alt_held = False
    _shift_held = False

    def _is_area_valid(self, area):
        """Check if an area is still valid without accessing type (which can crash)."""
        if not area:
            return False
        try:
            # Use a very safe check - just verify we can access a basic property
            # Don't access 'type' as it can crash on partially destroyed areas
            # Check 'spaces' which is safer, but wrap everything in broad exception handling
            _ = area.spaces
            # If we got here without exception, area is likely valid
            # But don't access 'type' as it can cause EXCEPTION_ACCESS_VIOLATION
            return True
        except Exception:
            # Any exception (including system-level crashes) means area is invalid
            return False

    def _is_region_valid(self, region):
        """Check if a region is still valid."""
        if not region:
            return False
        try:
            # Use a safe property check - don't access 'type' as it can crash
            _ = region.width
            return True
        except Exception:
            return False

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handles:
            return

        # Store area pointer for comparison during draw
        # as_pointer() gives us a stable memory address for the area
        self._invoke_area_ptr = context.area.as_pointer() if context.area else None
        self._area = None
        self._region = None

        # Register handlers for all major space types to ensure visibility across split views
        self._draw_handles = {}
        supported_types = [
            bpy.types.SpaceView3D,
            bpy.types.SpaceNodeEditor,
            bpy.types.SpaceImageEditor,
            bpy.types.SpaceSequenceEditor,
        ]

        for st in supported_types:
            handle = st.draw_handler_add(self._draw_callback, (), "WINDOW", "POST_PIXEL")
            self._draw_handles[st] = handle

    def _remove_draw_handler(self):
        if not self._draw_handles:
            return
        for st, handle in self._draw_handles.items():
            try:
                st.draw_handler_remove(handle, "WINDOW")
            except Exception:
                pass
        self._draw_handles = {}

    def _tag_redraw(self):
        """Tag all relevant areas for redraw to ensure overlay is visible."""
        try:
            # Tag all relevant areas since we don't store area references anymore
            # This ensures the overlay shows up regardless of which area is active
            # But we must be very careful not to access area.type on partially destroyed areas
            for window in bpy.context.window_manager.windows:
                try:
                    screen = window.screen
                    if not screen:
                        continue
                    for area in screen.areas:
                        # Don't access area.type directly - it can crash on destroyed areas
                        # Instead, try to tag_redraw and catch exceptions
                        try:
                            # Try to tag - if area is valid, this will work
                            # If area is destroyed, this will raise an exception
                            area.tag_redraw()
                        except Exception:
                            # Area is invalid or destroyed, skip it
                            pass
                except Exception:
                    # Window or screen is invalid, skip it
                    pass
        except Exception:
            # If anything fails, just continue - this is best effort
            pass

    def _draw_callback(self):
        """Draw callback for the overlay."""
        # Use bpy.context directly - it's more reliable for draw handlers
        context = bpy.context
        try:
            p = prefs(context)
        except (KeyError, AttributeError):
            # Addon is being disabled/unregistered, preferences no longer available
            return
        if not p.overlay_enabled:
            return

        # Only draw in the area where leader was invoked
        # Compare area pointers - as_pointer() gives stable memory addresses
        if self._invoke_area_ptr is not None and context.area is not None:
            try:
                if context.area.as_pointer() != self._invoke_area_ptr:
                    return  # Skip drawing in other areas
            except Exception:
                pass  # If we can't get pointer, just draw

        # Normal case: use context directly
        # Filter mappings by context for overlay display
        filtered_mappings = filter_mappings_by_context(p.mappings, self._context_type)

        # Use the buffer tokens for overlay rendering with filtered mappings
        # draw_overlay handles context.region being None gracefully (uses defaults: 600x400)
        buffer_tokens = self._buffer or []

        draw_overlay(context, p, buffer_tokens, filtered_mappings)

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start chord capture modal operation."""
        # Clean up any active test overlays
        disable_test_overlays()
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
        self._scroll_offset = 0
        self._ctrl_held = False
        self._alt_held = False
        self._shift_held = False

        # Detect the current editor context
        self._context_type = self._detect_context(context)

        # Hide T & N panels if enabled
        if p.overlay_hide_panels:
            self._hide_panels(context)

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
                if context.mode and context.mode.startswith('EDIT'):
                    return "VIEW_3D_EDIT"
                return "VIEW_3D"
            elif space_type == 'IMAGE_EDITOR':
                return "IMAGE_EDITOR"
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

    def _hide_panels(self, context: bpy.types.Context):
        """Hide T and N panels in the editor where Leader was invoked and all matching editor types."""
        self._panel_states = {}

        # Get the editor type where Leader was invoked
        invoke_space = context.space_data
        invoke_space_type = invoke_space.type if invoke_space else 'VIEW_3D'

        # Supported editor types that have T and N panels
        supported_types = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}

        # Iterate through all areas in all windows
        for window in context.window_manager.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    if not self._is_area_valid(area):
                        continue
                    try:
                        # Only hide panels in areas matching the invoke editor type
                        if area.type != invoke_space_type:
                            continue

                        # Skip if this editor type doesn't support panels
                        if area.type not in supported_types:
                            continue

                        # Get the space data
                        space = None
                        for s in area.spaces:
                            if s.type == invoke_space_type:
                                space = s
                                break

                        if not space:
                            continue

                        area_ptr = area.as_pointer()
                        panel_state = {}

                        # Store and hide N panel (Sidebar)
                        if hasattr(space, 'show_region_ui'):
                            panel_state['n_panel'] = space.show_region_ui
                            if space.show_region_ui:
                                space.show_region_ui = False

                        # Store and hide T panel (Toolbar/Toolshelf)
                        if hasattr(space, 'show_region_toolbar'):
                            panel_state['t_panel'] = space.show_region_toolbar
                            if space.show_region_toolbar:
                                space.show_region_toolbar = False

                        if panel_state:
                            # Store space type for restoration
                            panel_state['space_type'] = invoke_space_type
                            self._panel_states[area_ptr] = panel_state
                    except Exception:
                        continue
            except Exception:
                continue

    def _restore_panels(self, context: bpy.types.Context):
        """Restore T and N panels to their original visibility state."""
        if not self._panel_states:
            return

        # Iterate through all areas in all windows
        for window in context.window_manager.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    if not self._is_area_valid(area):
                        continue
                    try:
                        area_ptr = area.as_pointer()
                        if area_ptr not in self._panel_states:
                            continue

                        panel_state = self._panel_states[area_ptr]
                        space_type = panel_state.get('space_type', 'VIEW_3D')

                        # Only restore panels in areas matching the stored space type
                        if area.type != space_type:
                            continue

                        # Get the space data
                        space = None
                        for s in area.spaces:
                            if s.type == space_type:
                                space = s
                                break

                        if not space:
                            continue

                        # Restore N panel (Sidebar)
                        if 'n_panel' in panel_state and hasattr(space, 'show_region_ui'):
                            if space.show_region_ui != panel_state['n_panel']:
                                space.show_region_ui = panel_state['n_panel']

                        # Restore T panel (Toolbar/Toolshelf)
                        if 't_panel' in panel_state and hasattr(space, 'show_region_toolbar'):
                            if space.show_region_toolbar != panel_state['t_panel']:
                                space.show_region_toolbar = panel_state['t_panel']
                    except Exception:
                        continue
            except Exception:
                continue

        # Clear stored states
        self._panel_states = {}

    def _finish(self, context: bpy.types.Context, restore_panels=True):  # pylint: disable=unused-argument
        # Finish modal cleanup - reset all modifier tracking
        self._ctrl_held = False
        self._alt_held = False
        self._shift_held = False
        # Restore T & N panels if they were hidden (unless transitioning to Recents)
        if restore_panels:
            self._restore_panels(context)
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
        global _panel_states_global
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

        # Handle modifier key events BEFORE checking event.value to catch RELEASE events
        # Track CTRL
        if event.type in {"LEFT_CTRL", "RIGHT_CTRL"}:
            if event.value == "RELEASE":
                self._ctrl_held = False
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}
            elif event.value == "PRESS":
                self._ctrl_held = True
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}

        # Track ALT
        if event.type in {"LEFT_ALT", "RIGHT_ALT"}:
            if event.value == "RELEASE":
                self._alt_held = False
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}
            elif event.value == "PRESS":
                self._alt_held = True
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}

        # Track SHIFT
        if event.type in {"LEFT_SHIFT", "RIGHT_SHIFT"}:
            if event.value == "RELEASE":
                self._shift_held = False
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}
            elif event.value == "PRESS":
                self._shift_held = True
                self._last_mod_type = event.type
                return {"RUNNING_MODAL"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        # Modifier keys are already handled above, no need to track them here

        # Determine the side of the relevant modifier
        mod_side = None
        if self._last_mod_type:
            if "LEFT" in self._last_mod_type:
                mod_side = "LEFT"
            elif "RIGHT" in self._last_mod_type:
                mod_side = "RIGHT"

        # Normal token normalization - CTRL is always included in the token
        ctrl_held = getattr(self, '_ctrl_held', False) or event.ctrl

        tok = normalize_token(
            event.type,
            shift=event.shift,
            ctrl=event.ctrl,
            alt=event.alt,
            oskey=event.oskey,
            mod_side=mod_side
        )

        if tok is None:
            return {"RUNNING_MODAL"}

        # Reset last modifier type after a non-modifier key is processed
        self._last_mod_type = None

        # Check for <leader><leader>
        # If buffer is empty and user presses the leader key again, show recents
        leader_key = get_leader_key_type()
        if not self._buffer and event.type == leader_key:
            # Open recents instead of repeat
            # Don't restore panels here - Recents will handle them
            p = prefs(context)
            global _panel_states_global
            if p.overlay_hide_panels:
                # Transfer panel state to Recents by storing it globally
                # Recents will restore panels when it finishes
                _panel_states_global = self._panel_states.copy()
                # Clear our state so _finish doesn't restore
                self._panel_states = {}
            # Finish without restoring panels (they'll be handled by Recents)
            self._finish(context, restore_panels=False)
            try:
                bpy.ops.chordsong.recents('INVOKE_DEFAULT')
            except Exception as e:
                print(f"Chord Song: Failed to open recents: {e}")
                # If Recents failed, restore panels now
                if p.overlay_hide_panels:
                    self._panel_states = _panel_states_global.copy()
                    self._restore_panels(context)
                    _panel_states_global = {}
            return {"FINISHED"}

        # Normal mode - accumulate tokens in buffer
        self._buffer.append(tok)

        self._scroll_offset = 0  # Reset scroll when adding to buffer

        # Filter mappings by context
        filtered_mappings = filter_mappings_by_context(p.mappings, self._context_type)

        # Try exact match with current buffer
        m = find_exact_mapping(filtered_mappings, self._buffer)

        # If no match and a modifier is held, try matching without that modifier token
        # This handles cases where user presses Modifier+key but the mapping is just "key"
        # Get the configured multi-toggle modifier
        p = prefs(context)
        toggle_modifier = p.toggle_multi_modifier

        # Check if the configured modifier is held
        modifier_held = False
        modifier_symbol = ''
        if toggle_modifier == 'CTRL':
            modifier_held = ctrl_held
            modifier_symbol = '^'
        elif toggle_modifier == 'ALT':
            modifier_held = getattr(self, '_alt_held', False) or event.alt
            modifier_symbol = '!'
        elif toggle_modifier == 'SHIFT':
            modifier_held = getattr(self, '_shift_held', False) or event.shift
            modifier_symbol = '+'

        if not m and modifier_held:
            # Extract base keys from tokens that have the configured modifier
            # Use _get_token_parts to properly parse tokens like <^b into base 'b'
            from ..core.engine import _get_token_parts
            buffer_without_modifier = []
            for t in self._buffer:
                mods, base = _get_token_parts(t)
                # Check if this token has the configured modifier
                has_modifier = modifier_symbol in mods or f'<{modifier_symbol}' in mods or f'>{modifier_symbol}' in mods
                if has_modifier:
                    # Remove only the configured modifier, keep other modifiers
                    # e.g., '^+A' with modifier_symbol '^' becomes '+A'
                    remaining_mods = mods - {modifier_symbol, f'<{modifier_symbol}', f'>{modifier_symbol}'}
                    if remaining_mods:
                        # Reconstruct token with remaining modifiers in correct order
                        # Order: #, ^, !, +
                        ordered_mods = []
                        for mod_sym in ['#', '<#', '>#', '^', '<^', '>^', '!', '<!', '>!', '+', '<+', '>+']:
                            if mod_sym in remaining_mods:
                                ordered_mods.append(mod_sym)
                        reconstructed = ''.join(ordered_mods) + base
                        buffer_without_modifier.append(reconstructed)
                    elif base:
                        # No modifiers left, just use base
                        buffer_without_modifier.append(base)
                    # If no base (shouldn't happen), skip this token
                else:
                    # No matching modifier, keep token as-is
                    buffer_without_modifier.append(t)

            if buffer_without_modifier != self._buffer:
                # Buffer had modifier tokens, try matching without them
                toggle_mappings = [m for m in filtered_mappings if getattr(m, 'mapping_type', None) == 'CONTEXT_TOGGLE']
                if toggle_mappings:
                    toggle_match = find_exact_mapping(toggle_mappings, buffer_without_modifier)
                    if toggle_match:
                        # Found a toggle match without modifier - use that
                        m = toggle_match
                        # Update buffer to remove modifier tokens for consistency
                        self._buffer = buffer_without_modifier
        if m:
            mapping_type = getattr(m, "mapping_type", "OPERATOR")

            # Get label and icon for fading overlay
            label = getattr(m, "label", "") or "(no label)"
            icon = getattr(m, "icon", "") or ""

            # Capture the buffer before finishing
            chord_tokens = list(self._buffer)

            # Handle Python script execution
            if mapping_type == "PYTHON_FILE":
                # Check if custom scripts are enabled
                if not prefs(context).allow_custom_user_scripts:
                    self.report({"ERROR"}, "Script execution is disabled. Enable 'Allow Custom User Scripts' in Preferences.")
                    self._finish(context)
                    return {"CANCELLED"}

                python_file = (getattr(m, "python_file", "") or "").strip()
                if not python_file:
                    self.report({"WARNING"}, f'Chord "{" ".join(self._buffer)}" has no script file')
                    self._finish(context)
                    return {"CANCELLED"}

                # Capture viewport context BEFORE finishing modal (when we have valid context)
                ctx_viewport = capture_viewport_context(context)

                # Parse arguments for the script
                # Combine primary kwargs_json and all additional script_params
                all_kwargs_str = getattr(m, "kwargs_json", "") or ""
                for sp in getattr(m, "script_params", []):
                    if sp.value.strip():
                        if all_kwargs_str and not all_kwargs_str.strip().endswith(","):
                            all_kwargs_str += ", "
                        all_kwargs_str += sp.value.strip()

                script_args = parse_kwargs(all_kwargs_str)

                # Finish modal before executing script
                self._finish(context)

                # Execute Python script
                def execute_script_delayed():
                    try:
                        # Validate context before using it (may be invalid after undo)
                        from ..utils.render import validate_viewport_context, _execute_script_via_text_editor
                        valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

                        # Execute using Blender's text editor (avoids exec/runpy)
                        success, error_msg = _execute_script_via_text_editor(
                            python_file,
                            script_args=script_args,
                            valid_ctx=valid_ctx,
                            context=bpy.context
                        )

                        if not success:
                            print(f"Chord Song: {error_msg}")
                            return None

                        # Show fading overlay using the original captured context (ctx_viewport)
                        # This ensures overlay appears in the editor where leader was invoked
                        overlay_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                        if overlay_ctx and overlay_ctx.get("area") and overlay_ctx.get("region"):
                            try:
                                # Get space_data directly from the area (area.spaces[0] is the active space)
                                area = overlay_ctx["area"]
                                region = overlay_ctx["region"]
                                space_data = None
                                try:
                                    if area.spaces:
                                        space_data = area.spaces[0]
                                except Exception:
                                    pass

                                # Create a context-like object with the area from overlay_ctx
                                # This ensures we store the correct area pointer and space type
                                class ContextWrapper:
                                    def __init__(self, area, region, space_data):
                                        self.area = area
                                        self.region = region
                                        self.space_data = space_data

                                wrapped_ctx = ContextWrapper(area, region, space_data)
                                _show_fading_overlay(wrapped_ctx, chord_tokens, label, icon)
                            except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                        else:
                            _show_fading_overlay(bpy.context, chord_tokens, label, icon)

                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="PYTHON_FILE",
                            python_file=python_file,
                            kwargs=script_args,
                            execution_context=ctx_viewport,
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

                # Capture viewport context BEFORE modifying buffer
                ctx_viewport = capture_viewport_context(context)

                # Check if configured modifier is held - if so, remove last token and keep modal open
                # Get the configured modifier from preferences
                p = prefs(context)
                toggle_modifier = p.toggle_multi_modifier  # 'CTRL', 'ALT', 'SHIFT', or 'OSKEY'

                # Check if the configured modifier is held
                modifier_held = False
                if toggle_modifier == 'CTRL':
                    modifier_held = getattr(self, '_ctrl_held', False) or event.ctrl
                elif toggle_modifier == 'ALT':
                    modifier_held = getattr(self, '_alt_held', False) or event.alt
                elif toggle_modifier == 'SHIFT':
                    modifier_held = getattr(self, '_shift_held', False) or event.shift

                if not modifier_held:
                    # Normal behavior: finish modal after toggle
                    self._finish(context)
                else:
                    # Modifier held: remove the last token from buffer and keep modal open
                    # This puts us back to the state before the last key was pressed
                    if self._buffer:
                        self._buffer.pop()
                    self._scroll_offset = 0
                    self._tag_redraw()

                def execute_toggle_delayed():
                    try:
                        # Define helpers for context execution
                        def do_toggle_path(path):
                            parts = path.split('.')
                            obj = bpy.context
                            for part in parts[:-1]:
                                next_obj = getattr(obj, part, None)
                                if next_obj is None:
                                    return None
                                obj = next_obj
                            prop_name = parts[-1]
                            if not hasattr(obj, prop_name):
                                return None
                            current_value = getattr(obj, prop_name)
                            if not isinstance(current_value, bool):
                                return None
                            set_val = not current_value
                            setattr(obj, prop_name, set_val)
                            return set_val

                        def do_set_path(path, value):
                            parts = path.split('.')
                            obj = bpy.context
                            for part in parts[:-1]:
                                next_obj = getattr(obj, part, None)
                                if next_obj is None:
                                    return None
                                obj = next_obj
                            prop_name = parts[-1]
                            if not hasattr(obj, prop_name):
                                return None
                            setattr(obj, prop_name, value)
                            return value

                        # Collect all paths
                        paths = []
                        if context_path:
                            paths.append(context_path)
                        for item in m.sub_items:
                            if item.path.strip():
                                paths.append(item.path.strip())

                        # Execute state logic
                        sync = getattr(m, "sync_toggles", False)
                        results = []
                        master_new_val = None

                        def run_logic():
                            nonlocal master_new_val
                            for i, path in enumerate(paths):
                                if i == 0:
                                    master_new_val = do_toggle_path(path)
                                    if master_new_val is not None:
                                        results.append(master_new_val)
                                else:
                                    if sync and master_new_val is not None:
                                        res = do_set_path(path, master_new_val)
                                    else:
                                        res = do_toggle_path(path)
                                    if res is not None:
                                        results.append(res)

                        # Validate context before using it (may be invalid after undo)
                        from ..utils.render import validate_viewport_context
                        valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

                        # Execute with context override if available
                        if valid_ctx:
                            try:
                                with bpy.context.temp_override(**valid_ctx):
                                    run_logic()
                            except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                # Context became invalid, fall back to default context
                                run_logic()
                        else:
                            run_logic()

                        # Show fading overlay with multi-status if applicable
                        # Skip fading overlay if modifier is held (modal stays open)
                        if results and not modifier_held:
                            overlay_label = ""
                            if len(results) == 1:
                                status = "ON" if results[0] else "OFF"
                                overlay_label = f"{label} ({status})"
                            else:
                                # Show count or joined status
                                on_count = sum(1 for r in results if r)
                                off_count = len(results) - on_count
                                status_str = f"{on_count} ON, {off_count} OFF"
                                overlay_label = f"{label} ({status_str})"

                            # Use the original captured viewport context (ctx_viewport) for overlay
                            overlay_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                            if overlay_ctx and overlay_ctx.get("area") and overlay_ctx.get("region"):
                                try:
                                    # Get space_data directly from the area (area.spaces[0] is the active space)
                                    area = overlay_ctx["area"]
                                    region = overlay_ctx["region"]
                                    space_data = None
                                    try:
                                        if area.spaces:
                                            space_data = area.spaces[0]
                                    except Exception:
                                        pass

                                    # Create a context-like object with the area from overlay_ctx
                                    class ContextWrapper:
                                        def __init__(self, area, region, space_data):
                                            self.area = area
                                            self.region = region
                                            self.space_data = space_data

                                    wrapped_ctx = ContextWrapper(area, region, space_data)
                                    _show_fading_overlay(wrapped_ctx, chord_tokens, overlay_label, icon)
                                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                    _show_fading_overlay(bpy.context, chord_tokens, overlay_label, icon)
                            else:
                                _show_fading_overlay(bpy.context, chord_tokens, overlay_label, icon)

                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="CONTEXT_TOGGLE",
                            context_path=context_path,
                            execution_context=ctx_viewport,
                        )

                        # Clear overlay cache so toggle state is re-evaluated on next redraw
                        from ..ui.overlay.cache import clear_overlay_cache
                        clear_overlay_cache()
                        # Force redraw to update toggle icon immediately
                        # In toggle multi-execution mode, ensure overlay refreshes with all toggle mappings
                        self._tag_redraw()

                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to toggle context '{context_path}': {e}")
                        traceback.print_exc()
                    return None

                bpy.app.timers.register(execute_toggle_delayed, first_interval=0.01)

                # If modifier is held, keep modal running; otherwise finish
                if modifier_held:
                    return {"RUNNING_MODAL"}
                else:
                    return {"FINISHED"}

            # Handle context property execution
            if mapping_type == "CONTEXT_PROPERTY":
                context_path = (getattr(m, "context_path", "") or "").strip()
                property_value = (getattr(m, "property_value", "") or "").strip()
                if not context_path:
                    self.report({"ERROR"}, f'Property mapping "{" ".join(self._buffer)}" has no context path. Please fix in preferences.')
                    self._finish(context)
                    return {"CANCELLED"}

                # Capture viewport context BEFORE finishing modal
                ctx_viewport = capture_viewport_context(context)

                self._finish(context)

                def execute_property_delayed():
                    try:
                        import ast
                        # Helper to execute a single set
                        def do_set_item(path, val_str):
                            if not path or not val_str:
                                return False

                            try:
                                val_to_set = ast.literal_eval(val_str)
                            except (ValueError, SyntaxError):
                                val_to_set = val_str

                            parts = path.split('.')
                            obj = bpy.context

                            # Navigate to the parent object
                            for _, part in enumerate(parts[:-1]):
                                next_obj = getattr(obj, part, None)
                                if next_obj is None:
                                    return False
                                obj = next_obj

                            # Get the property name
                            prop_name = parts[-1]

                            # Set the value
                            if not hasattr(obj, prop_name):
                                return False

                            setattr(obj, prop_name, val_to_set)
                            return True

                        # Collect all pairs
                        items = []
                        if context_path:
                            items.append((context_path, property_value))
                        for sub in m.sub_items:
                            if sub.path.strip():
                                items.append((sub.path.strip(), sub.value))

                        # Validate context before using it (may be invalid after undo)
                        from ..utils.render import validate_viewport_context
                        valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

                        success_count = 0

                        # Execute with context override if available
                        if valid_ctx:
                            try:
                                with bpy.context.temp_override(**valid_ctx):
                                    for p, v in items:
                                        if do_set_item(p, v):
                                            success_count += 1
                            except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                # Fallback
                                for p, v in items:
                                    if do_set_item(p, v):
                                        success_count += 1
                        else:
                            for p, v in items:
                                if do_set_item(p, v):
                                    success_count += 1

                        if success_count > 0:
                            overlay_label = ""
                            if success_count == 1:
                                overlay_label = f"{label}: {property_value}"
                            else:
                                overlay_label = f"{label}: {success_count} values set"

                            # Use the original captured viewport context (ctx_viewport) for overlay
                            overlay_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                            if overlay_ctx and overlay_ctx.get("area") and overlay_ctx.get("region"):
                                try:
                                    # Get space_data directly from the area (area.spaces[0] is the active space)
                                    area = overlay_ctx["area"]
                                    region = overlay_ctx["region"]
                                    space_data = None
                                    try:
                                        if area.spaces:
                                            space_data = area.spaces[0]
                                    except Exception:
                                        pass

                                    # Create a context-like object with the area from overlay_ctx
                                    class ContextWrapper:
                                        def __init__(self, area, region, space_data):
                                            self.area = area
                                            self.region = region
                                            self.space_data = space_data

                                    wrapped_ctx = ContextWrapper(area, region, space_data)
                                    _show_fading_overlay(wrapped_ctx, chord_tokens, overlay_label, icon)
                                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                    _show_fading_overlay(bpy.context, chord_tokens, overlay_label, icon)
                            else:
                                _show_fading_overlay(bpy.context, chord_tokens, overlay_label, icon)

                        # Add to history
                        add_to_history(
                            chord_tokens=chord_tokens,
                            label=label,
                            icon=icon,
                            mapping_type="CONTEXT_PROPERTY",
                            context_path=context_path,
                            property_value=property_value,
                            execution_context=ctx_viewport,
                        )

                    except Exception as e:
                        import traceback
                        print(f"Chord Song: Failed to set property '{context_path}': {e}")
                        traceback.print_exc()
                    return None

                bpy.app.timers.register(execute_property_delayed, first_interval=0.01)
                return {"FINISHED"}

            # Handle operator execution
            operators_to_run = []

            primary_op = (m.operator or "").strip()
            if primary_op:
                operators_to_run.append({
                    "op": primary_op,
                    "kwargs": parse_kwargs(getattr(m, "kwargs_json", "{}")),
                    "call_ctx": (getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
                })

            for sub in m.sub_operators:
                sub_op = (sub.operator or "").strip()
                if sub_op:
                    operators_to_run.append({
                        "op": sub_op,
                        "kwargs": parse_kwargs(getattr(sub, "kwargs_json", "{}")),
                        "call_ctx": (getattr(sub, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
                    })

            if not operators_to_run:
                self.report({"WARNING"}, f'Chord "{" ".join(self._buffer)}" has no operator')
                self._finish(context)
                return {"CANCELLED"}

            # Capture viewport context BEFORE finishing modal
            ctx_viewport = capture_viewport_context(context)

            # Check if we're executing scripts_overlay - if so, transfer panel states
            # (scripts_overlay will handle panel hiding/restoration)
            primary_operator = operators_to_run[0]["op"] if operators_to_run else None
            should_restore_panels = (primary_operator != "chordsong.scripts_overlay")

            # If executing scripts_overlay, transfer panel states to global storage
            if not should_restore_panels and p.overlay_hide_panels:
                # Transfer panel state to Scripts overlay by storing it globally
                # Scripts overlay will restore panels when it finishes
                _panel_states_global = self._panel_states.copy()
                # Clear our state so _finish doesn't restore
                self._panel_states = {}

            # Finish the modal operator FIRST
            self._finish(context, restore_panels=should_restore_panels)

            # Defer operator execution to next frame using a timer.
            def execute_operator_delayed():
                try:
                    # Validate context before using it
                    from ..utils.render import validate_viewport_context
                    valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

                    success = False

                    for op_data in operators_to_run:
                        op = op_data["op"]
                        kwargs = op_data["kwargs"]
                        call_ctx = op_data["call_ctx"]

                        mod_name, fn_name = op.split(".", 1)
                        opmod = getattr(bpy.ops, mod_name)
                        opfn = getattr(opmod, fn_name)

                        result_set = set()
                        if call_ctx == "INVOKE_DEFAULT":
                            if valid_ctx:
                                try:
                                    with bpy.context.temp_override(**valid_ctx):
                                        result_set = opfn('INVOKE_DEFAULT', **kwargs)
                                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                    result_set = opfn('INVOKE_DEFAULT', **kwargs)
                            else:
                                result_set = opfn('INVOKE_DEFAULT', **kwargs)
                        else:
                            if valid_ctx:
                                try:
                                    with bpy.context.temp_override(**valid_ctx):
                                        result_set = opfn('EXEC_DEFAULT', **kwargs)
                                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                    result_set = opfn('EXEC_DEFAULT', **kwargs)
                            else:
                                result_set = opfn('EXEC_DEFAULT', **kwargs)

                        if result_set and ('FINISHED' in result_set or 'CANCELLED' not in result_set):
                            success = True

                    if success:
                        # Skip fading overlay and history for scripts_overlay operator (it handles its own overlay and adds scripts to history)
                        primary_operator = operators_to_run[0]["op"] if operators_to_run else None
                        if primary_operator != "chordsong.scripts_overlay":
                            # Use the original captured viewport context (ctx_viewport) for overlay
                            # This ensures we show overlay in the editor where leader was invoked
                            # Validate it first to ensure it's still valid
                            overlay_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                            if overlay_ctx and overlay_ctx.get("area") and overlay_ctx.get("region"):
                                try:
                                    # Get space_data directly from the area (area.spaces[0] is the active space)
                                    area = overlay_ctx["area"]
                                    region = overlay_ctx["region"]
                                    space_data = None
                                    try:
                                        if area.spaces:
                                            space_data = area.spaces[0]
                                    except Exception:
                                        pass

                                    # Create a context-like object with the area from overlay_ctx
                                    class ContextWrapper:
                                        def __init__(self, area, region, space_data):
                                            self.area = area
                                            self.region = region
                                            self.space_data = space_data

                                    wrapped_ctx = ContextWrapper(area, region, space_data)
                                    _show_fading_overlay(wrapped_ctx, chord_tokens, label, icon)
                                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                                    # Context became invalid, fall back to current context
                                    _show_fading_overlay(bpy.context, chord_tokens, label, icon)
                            else:
                                _show_fading_overlay(bpy.context, chord_tokens, label, icon)

                            # Don't add scripts_overlay operator to history (scripts executed through it are added separately)
                            add_to_history(
                                chord_tokens=chord_tokens,
                                label=label,
                                icon=icon,
                                mapping_type="OPERATOR",
                                operator=operators_to_run[0]["op"], # Log the primary operator
                                kwargs=operators_to_run[0]["kwargs"],
                                call_context=operators_to_run[0]["call_ctx"],
                                execution_context=ctx_viewport,
                            )

                except Exception as e:
                    import traceback
                    print(f"Chord Song: Failed to execute operators: {e}")
                    traceback.print_exc()
                return None

            bpy.app.timers.register(execute_operator_delayed, first_interval=0.01)
            return {"FINISHED"}

        # Still a prefix?
        cands = candidates_for_prefix(filtered_mappings, self._buffer, context=context)
        if cands:
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # No match - remove only the last token and keep modal running so user can try again
        chord_str = humanize_chord(self._buffer)
        self.report({"WARNING"}, f'Unknown chord: "{chord_str}"')
        if self._buffer:
            self._buffer.pop()  # Remove only the last token
        self._tag_redraw()
        return {"RUNNING_MODAL"}
