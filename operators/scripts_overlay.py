"""Scripts overlay operator for quick script access."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

import os
import bpy  # type: ignore
from ..ui.overlay import draw_overlay
from ..utils.fuzzy import fuzzy_match
from .common import prefs


class CHORDSONG_OT_ScriptsOverlay(bpy.types.Operator):
    """Show overlay with available scripts from scripts folder"""

    bl_idname = "chordsong.scripts_overlay"
    bl_label = "Scripts Overlay"
    bl_options = {'REGISTER'}

    _draw_handles = {}
    _buffer = None
    _text_buffer = ""  # Text input buffer for filtering
    _all_scripts_list = []  # All scripts before filtering
    _filtered_scripts_list = []  # Filtered scripts (max 9 for 1-9 chords)
    _invoke_area_ptr = None
    _panel_states = {}  # Store original panel visibility states: {area_ptr: {"n_panel": bool, "t_panel": bool}}

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handles:
            return

        self._invoke_area_ptr = context.area.as_pointer() if context.area else None
        self._area = context.area
        self._region = context.region

        # Register handlers for all major space types
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
        """Tag all relevant areas for redraw."""
        try:
            for window in bpy.context.window_manager.windows:
                try:
                    screen = window.screen
                    if not screen:
                        continue
                    for area in screen.areas:
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    def _filter_scripts(self):
        """Filter scripts based on text buffer using fuzzy matching."""
        if not self._text_buffer:
            # No filter, show all scripts
            self._filtered_scripts_list = self._all_scripts_list
            return

        # Filter scripts using fuzzy matching
        scored_scripts = []
        for script_name, script_path in self._all_scripts_list:
            matched, score = fuzzy_match(self._text_buffer, script_name)
            if matched:
                scored_scripts.append((score, script_name, script_path))

        # Sort by score (lower is better) and show all matches
        scored_scripts.sort(key=lambda x: x[0])
        self._filtered_scripts_list = [(name, path) for _, name, path in scored_scripts]

    def _draw_callback(self):
        """Draw callback for the scripts overlay."""
        context = bpy.context
        try:
            p = prefs(context)
        except (KeyError, AttributeError):
            return
        if not p.overlay_enabled:
            return

        # Safety check: if script execution is disabled, clean up and exit
        if not p.allow_custom_user_scripts:
            self._remove_draw_handler()
            return

        # Safety check: ensure scripts list is initialized (operator was properly invoked)
        if not hasattr(self, '_all_scripts_list') or self._all_scripts_list is None:
            self._remove_draw_handler()
            return

        # Only draw in the area where overlay was invoked
        if self._invoke_area_ptr is not None and context.area is not None:
            try:
                if context.area.as_pointer() != self._invoke_area_ptr:
                    return
            except Exception:
                pass

        # Use the stored region from invoke if available to prevent crashes when
        # context.region is None or invalid (e.g., in new files, custom scripts, overlays)
        if hasattr(self, '_region') and self._region:
            # Create a temporary context wrapper that uses our stored region
            class ContextWithRegion:
                def __init__(self, original_ctx, region, area):
                    self._ctx = original_ctx
                    self.region = region
                    self.area = area
                def __getattr__(self, name):
                    return getattr(self._ctx, name)
            
            context = ContextWithRegion(bpy.context, self._region, self._area)

        # Filter scripts based on text buffer
        self._filter_scripts()

        # Create fake mappings from filtered scripts list for overlay rendering
        fake_mappings = []

        # Create a simple object to mimic a mapping
        class FakeMapping:
            def __init__(self, chord, label, script_path, icon=""):
                self.chord = chord
                self.label = label
                self.icon = icon
                self.group = "Scripts"
                self.context = "ALL"
                self.mapping_type = "PYTHON_FILE"
                self.python_file = script_path
                self.operator = ""  # For OPERATOR type mappings
                self.enabled = True
                self.kwargs_json = ""
                self.call_context = "EXEC_DEFAULT"
                self.sub_items = []
                self.sub_operators = []
                self.script_params = []

        # Build buffer tokens from text buffer for header display
        # Pass as single token to display as one string without "+" separators
        buffer_tokens = [self._text_buffer] if self._text_buffer else []

        # Get max items from preferences
        max_items = p.scripts_overlay_max_items

        # Create chords that match the buffer prefix so candidates_for_prefix doesn't filter them out
        # The chord format is: text_buffer + " " + number
        # Numbering: 1, 2, 3, ..., 9 (so index 0->1, index 1->2, ..., index 8->9)
        # Only assign chords to first 9 items, but show all filtered scripts up to max_items
        # Python nerd icon (󰌠) is used for scripts beyond the first 9
        python_icon = "󰌠"  # Python nerd icon

        for i, (script_name, script_path) in enumerate(self._filtered_scripts_list):
            if i >= max_items:
                # Don't create mappings beyond max_items
                break

            if i < 9:
                # Assign chord: 1-9
                # Map index 0->1, 1->2, ..., 8->9
                chord_num = str(i + 1)

                # Create chord that starts with text buffer, then space, then number
                if self._text_buffer:
                    chord = f"{self._text_buffer} {chord_num}"  # e.g., "abc 1", "abc 2", ..., "abc 0"
                else:
                    chord = chord_num  # 1, 2, ..., 9, 0 when no buffer

                # First 9 items: use Python icon after chord
                icon = python_icon
                label = script_name
                fake_mappings.append(FakeMapping(chord, label, script_path, icon))
            else:
                # Items beyond first 9: display but don't assign executable chords
                # Use a non-executable chord that won't be displayed (empty or special marker)
                # These scripts can only be accessed by filtering to bring them into positions 1-9
                chord = ""  # Empty chord - won't be displayed and can't be executed

                # Items beyond first 9: use Python nerd icon
                icon = python_icon
                label = script_name
                fake_mappings.append(FakeMapping(chord, label, script_path, icon))

        # Calculate total scripts count for header display
        total_scripts = len(self._filtered_scripts_list)
        script_count_text = f"{total_scripts} Script{'s' if total_scripts != 1 else ''}"

        # Prepare scripts overlay specific settings
        scripts_overlay_settings = {
            "column_rows": p.scripts_overlay_column_rows,
            "max_label_length": p.scripts_overlay_max_label_length,
            "gap": p.scripts_overlay_gap,
            "column_gap": p.scripts_overlay_column_gap,
        }

        # Use the overlay rendering with fake mappings
        # Pass buffer tokens so they appear in header (as single token to avoid "+" separators)
        # Pass custom header text to show script count instead of file name
        # Pass scripts overlay specific settings
        draw_overlay(context, p, buffer_tokens, fake_mappings,
                    custom_header=script_count_text,
                    scripts_overlay_settings=scripts_overlay_settings)

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start scripts overlay modal operation."""
        p = prefs(context)
        p.ensure_defaults()

        # Check if custom scripts are enabled FIRST (before any other operations)
        if not p.allow_custom_user_scripts:
            # Show warning in fading overlay
            from ..operators.leader import _show_fading_overlay
            warning_message = "Script execution disabled. Enable in Preferences."
            warning_icon = "󰀪"  # Nerd Font warning icon (or use empty string if not available)
            _show_fading_overlay(context, [], warning_message, warning_icon, show_chord=False)
            self.report({'WARNING'}, "Custom user scripts are disabled. Enable them in preferences.")
            # Ensure any existing draw handlers are cleaned up
            self._remove_draw_handler()
            return {'CANCELLED'}

        # If panels were hidden by Leader, keep them hidden
        # Retrieve panel state from global storage if available
        self._panel_states = {}
        if p.overlay_hide_panels:
            from ..operators.leader import _panel_states_global
            if _panel_states_global:
                # Use panel states from Leader (panels already hidden)
                self._panel_states = _panel_states_global.copy()
                # Clear the stored state so it doesn't persist
                _panel_states_global.clear()
            else:
                # No panel states from Leader, hide panels fresh
                self._hide_panels(context)

        # Get scripts folder
        scripts_folder = p.scripts_folder
        if not scripts_folder or not os.path.isdir(scripts_folder):
            self.report({'WARNING'}, "Scripts folder not set or doesn't exist. Set it in preferences.")
            return {'CANCELLED'}

        # Scan scripts folder for .py files
        self._all_scripts_list = []
        try:
            for filename in sorted(os.listdir(scripts_folder)):
                if filename.endswith('.py') and not filename.startswith('__'):
                    script_path = os.path.join(scripts_folder, filename)
                    script_name = filename[:-3]  # Remove .py extension
                    self._all_scripts_list.append((script_name, script_path))
        except Exception as e:
            self.report({'ERROR'}, f"Failed to scan scripts folder: {e}")
            return {'CANCELLED'}

        if not self._all_scripts_list:
            self.report({'INFO'}, "No scripts found in scripts folder")
            return {'CANCELLED'}

        self._buffer = []
        self._text_buffer = ""
        self._filtered_scripts_list = []
        self._filter_scripts()  # Initial filter (shows all scripts)
        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        # Restore T & N panels if they were hidden
        self._restore_panels(context)
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted."""
        self._finish(context)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        # Safety check: if script execution is disabled, cancel immediately
        try:
            p = prefs(context)
            if not p.allow_custom_user_scripts:
                self._finish(context)
                return {"CANCELLED"}
        except (KeyError, AttributeError):
            self._finish(context)
            return {"CANCELLED"}

        # Cancel keys
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}

        # Backspace to remove last character
        if event.type == "BACK_SPACE" and event.value == "PRESS":
            if self._text_buffer:
                self._text_buffer = self._text_buffer[:-1]
                self._tag_redraw()
                return {"RUNNING_MODAL"}
            else:
                # No text buffer, treat as cancel
                self._finish(context)
                return {"CANCELLED"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        # Handle number keys 0-9
        # Blender uses "ONE", "TWO", etc. for main row and "NUMPAD_1", etc. for numpad
        number_key_map = {
            "ZERO": 0, "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4,
            "FIVE": 5, "SIX": 6, "SEVEN": 7, "EIGHT": 8, "NINE": 9,
            **{f"NUMPAD_{i}": i for i in range(10)},
            **{f"{i}": i for i in range(10)},  # Also check numeric strings for compatibility
        }

        if event.type in number_key_map:
            chord_num = number_key_map[event.type]

            # If Ctrl, Alt, or Shift is pressed, add number to text buffer for filtering
            if event.ctrl or event.alt or event.shift:
                self._text_buffer += str(chord_num)
                self._tag_redraw()
                return {"RUNNING_MODAL"}
            else:
                # No modifier: execute script
                # Map chord number to index: 1->0, 2->1, ..., 9->8
                if chord_num == 0:
                    return {"RUNNING_MODAL"}  # 0 is not a valid chord
                idx = chord_num - 1

                if idx < len(self._filtered_scripts_list) and idx < 9:
                    script_name, script_path = self._filtered_scripts_list[idx]
                    # Build chord text for fading overlay
                    chord_num = str(idx + 1)
                    if self._text_buffer:
                        chord_text = f"{self._text_buffer} {chord_num}"
                    else:
                        chord_text = chord_num
                    self._finish(context)
                    # Show fading overlay and execute script
                    self._show_fading_and_execute(context, chord_text, script_name, script_path)
                    return {"FINISHED"}

        # Handle letter keys A-Z for text input (filtering)
        elif event.type in {chr(i) for i in range(ord('A'), ord('Z') + 1)}:
            # Convert to lowercase and add to text buffer
            char = event.type.lower()
            self._text_buffer += char
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}

    def _show_fading_and_execute(self, context, chord_text, script_name, script_path):
        """Show fading overlay and execute script."""
        from ..operators.leader import _show_fading_overlay
        from ..core.history import add_to_history

        # Python nerd icon for scripts
        python_icon = "󰌠"

        # Capture viewport context before finishing
        from ..utils.render import capture_viewport_context
        ctx_viewport = capture_viewport_context(context)

        # Show fading overlay with Python icon, but don't show chord text for scripts
        _show_fading_overlay(context, [chord_text], script_name, python_icon, show_chord=False)

        # Execute script
        def execute_delayed():
            try:
                from ..utils.render import _execute_script_via_text_editor, validate_viewport_context

                # Validate context before using it (may be invalid after undo)
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

                # Execute script
                success, error_msg = _execute_script_via_text_editor(
                    script_path,
                    script_args={},
                    valid_ctx=valid_ctx,
                    context=bpy.context
                )

                if not success:
                    print(f"Chord Song Scripts Overlay: {error_msg}")
                else:
                    self.report({'INFO'}, f"Executed: {script_name}")

                    # Add script to history/recents after successful execution
                    # Don't include chord tokens for scripts in recents
                    add_to_history(
                        chord_tokens=[],
                        label=script_name,
                        icon=python_icon,
                        mapping_type="PYTHON_FILE",
                        python_file=script_path,
                        kwargs={},
                        execution_context=ctx_viewport,
                    )

            except Exception as e:
                import traceback
                print(f"Chord Song Scripts Overlay: Failed to execute script: {e}")
                traceback.print_exc()
            return None

        bpy.app.timers.register(execute_delayed, first_interval=0.01)

    def _is_area_valid(self, area):
        """Check if an area is still valid without accessing type (which can crash)."""
        if not area:
            return False
        try:
            # Use a very safe check - just verify we can access a basic property
            # Don't access 'type' as it can crash on partially destroyed areas
            _ = area.spaces
            return True
        except Exception:
            return False

    def _hide_panels(self, context: bpy.types.Context):
        """Hide T and N panels in the editor where Scripts overlay was invoked and all matching editor types."""
        self._panel_states = {}
        
        # Get the editor type where Scripts overlay was invoked
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



