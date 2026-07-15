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
    bl_options = set()

    # Class-level defaults are immutable sentinels. Invoke rebinds these on
    # `self`; _cancel_requested intentionally stays class-level as a shared
    # signal for re-invocation to request the active instance to stop.
    _draw_handles = None
    _buffer = None
    _text_buffer = ""
    _all_scripts_list = None
    _scan_warnings = None
    _filtered_scripts_list = None
    _invoke_area_ptr = None
    _panel_states = None
    _cancel_requested = False  # Shared across invocations by design
    _hover_script_path = None

    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handles:
            return

        # Use override area/region if set (e.g. when invoked from Preferences)
        area = getattr(self, '_override_area', None) or context.area
        region = getattr(self, '_override_region', None) or context.region

        self._invoke_area_ptr = area.as_pointer() if area else None
        self._area = area
        self._region = region

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
        """Filter script entries against the text buffer using fuzzy matching."""
        if not self._text_buffer:
            self._filtered_scripts_list = self._all_scripts_list
            return

        scored = []
        for entry in self._all_scripts_list:
            haystack = f"{entry.name} {entry.group}" if entry.group else entry.name
            matched, score = fuzzy_match(self._text_buffer, haystack)
            if matched:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0])
        self._filtered_scripts_list = [entry for _, entry in scored]

    def _draw_callback(self):
        """Draw callback for the scripts overlay."""
        try:
            self._draw_callback_safe()
        except ReferenceError:
            # Operator's StructRNA has been freed (typical during blinker hot
            # reload — the draw handler outlives the operator instance for a
            # few frames). Silently skip; the unregister path tears down
            # handlers on the next cleanup_all_handlers() call.
            return
        except Exception:
            # Defence in depth: never raise from a draw callback.
            return

    def _draw_callback_safe(self):
        from .leader import _is_reloading
        if _is_reloading():
            return
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
            from ..utils.render import ContextWithRegion
            context = ContextWithRegion(bpy.context, self._region, self._area)

        # Filter scripts based on text buffer
        self._filter_scripts()

        # Create fake mappings from filtered scripts list for overlay rendering
        fake_mappings = []

        # Create a simple object to mimic a mapping
        class FakeMapping:
            def __init__(self, chord, label, script_path, icon="", group="", flagged=False):
                self.chord = chord
                self.label = label
                self.icon = icon
                self.group = group
                self.flagged = flagged
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

        # Build buffer tokens from text buffer — split into words so they
        # align with split_chord() which splits chords by whitespace.
        buffer_tokens = self._text_buffer.split() if self._text_buffer else []

        # Get max items from preferences
        max_items = p.scripts_overlay_max_items

        # Create chords that match the buffer prefix so candidates_for_prefix doesn't filter them out
        # The chord format is: text_buffer + " " + number
        # Numbering: 1, 2, 3, ..., 9 (so index 0->1, index 1->2, ..., index 8->9)
        # Only assign chords to first 9 items, but show all filtered scripts up to max_items
        # Python nerd icon (󰌠) is used for scripts beyond the first 9
        python_icon = "󰌠"  # Python nerd icon

        for i, entry in enumerate(self._filtered_scripts_list):
            if i >= max_items:
                break

            if i < 9:
                chord_num = str(i + 1)
                if self._text_buffer:
                    chord = f"{self._text_buffer} {chord_num}"
                else:
                    chord = chord_num
            else:
                # Beyond first 9: displayed but not chord-executable
                chord = ""

            # Group shown as secondary text (":: Group") — splits into
            # label_extra in build_overlay_rows, red when flagged (render).
            label = entry.name
            if entry.group:
                label = f"{entry.name} :: {entry.group}"
            fake_mappings.append(FakeMapping(
                chord, label, entry.path, python_icon,
                group=entry.group or "Scripts", flagged=entry.flagged,
            ))

        # Calculate total scripts count for header display
        total_scripts = len(self._filtered_scripts_list)
        script_count_text = f"{total_scripts} Script{'s' if total_scripts != 1 else ''}"
        if self._scan_warnings:
            script_count_text += "  —  󰀪 Unrecognized folders detected"

        # Prepare scripts overlay specific settings
        scripts_overlay_settings = {
            "column_rows": p.scripts_overlay_column_rows,
            "max_label_length": p.scripts_overlay_max_label_length,
            "gap": p.scripts_overlay_gap,
            "column_gap": p.scripts_overlay_column_gap,
            "hover_script_path": self._hover_script_path,
        }

        # Use the overlay rendering with fake mappings
        # Pass buffer tokens so they appear in header (as single token to avoid "+" separators)
        # Pass custom header text to show script count instead of file name
        # Pass scripts overlay specific settings
        draw_overlay(context, p, buffer_tokens, fake_mappings,
                    custom_header=script_count_text,
                    scripts_overlay_settings=scripts_overlay_settings)

    def _find_viewport_area(self, context):
        """Find a suitable viewport area for overlay drawing.

        When invoked from a non-viewport context (e.g. Preferences panel),
        the current area can't host draw handlers. Search all windows for
        a supported area and return (area, region) or (None, None).
        """
        supported = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}
        for window in context.window_manager.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    if area.type in supported:
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                return area, region
            except Exception:
                continue
        return None, None

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start scripts overlay modal operation."""
        # If already running, request cancellation (acts as toggle)
        if CHORDSONG_OT_ScriptsOverlay._draw_handles:
            CHORDSONG_OT_ScriptsOverlay._cancel_requested = True
            self._tag_redraw()
            return {'CANCELLED'}

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

        # If invoked from a non-viewport area (e.g. Preferences debug panel),
        # find a suitable viewport area to host the overlay
        supported = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}
        area = context.area
        region = context.region
        if area and area.type not in supported:
            area, region = self._find_viewport_area(context)
            if not area:
                self.report({'WARNING'}, "No viewport area found for overlay")
                return {'CANCELLED'}
        # Store the resolved area/region for draw handler setup
        self._override_area = area
        self._override_region = region

        # If Leader already hid panels before handing off to this overlay,
        # pick up the stash so we restore the same state on close. Otherwise
        # hide them fresh.
        from ..utils.panels import hide_panels, take_panel_states
        stashed = take_panel_states()
        if stashed:
            self._panel_states = stashed
        else:
            self._panel_states = hide_panels(context, p.overlay_hide_panels)

        # Get scripts folder
        scripts_folder = p.scripts_folder
        if not scripts_folder or not os.path.isdir(scripts_folder):
            self.report({'WARNING'}, "Scripts folder not set or doesn't exist. Set it in preferences.")
            return {'CANCELLED'}

        # Scan scripts folder (context folders, groups, .chordsong aliases)
        from ..core.script_scanner import scan_scripts_folder, sort_entries
        from .common import current_script_contexts
        try:
            entries, scan_warnings = scan_scripts_folder(scripts_folder)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to scan scripts folder: {e}")
            return {'CANCELLED'}

        current = current_script_contexts(context)
        visible = [e for e in entries
                   if e.context_token is None or e.context_token in current]
        self._all_scripts_list = sort_entries(
            visible, getattr(p, "scripts_overlay_folders_first", True))
        self._scan_warnings = scan_warnings
        for w in scan_warnings:
            print(f"Chord Song Scripts Overlay: {w}")

        if not self._all_scripts_list:
            self.report({'INFO'}, "No scripts found in scripts folder")
            return {'CANCELLED'}

        self._buffer = []
        self._text_buffer = ""
        self._filtered_scripts_list = []
        self._hover_script_path = None
        self._filter_scripts()  # Initial filter (shows all scripts)
        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        CHORDSONG_OT_ScriptsOverlay._cancel_requested = False
        # Restore T & N panels if they were hidden
        self._restore_panels(context)
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted."""
        self._finish(context)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        try:
            return self._modal_inner(context, event)
        except Exception:
            import traceback
            traceback.print_exc()
            print("Chord Song Scripts Overlay: modal crashed, cleaning up to prevent busy state.")
            try:
                self._finish(context)
            except Exception:
                self._remove_draw_handler()
            return {"CANCELLED"}

    def _modal_inner(self, context: bpy.types.Context, event: bpy.types.Event):
        from .leader import _is_reloading
        if _is_reloading():
            self._finish(context)
            return {"CANCELLED"}
        # Check if cancellation was requested from re-invocation (toggle)
        if CHORDSONG_OT_ScriptsOverlay._cancel_requested:
            CHORDSONG_OT_ScriptsOverlay._cancel_requested = False
            self._finish(context)
            return {"CANCELLED"}

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

        # Hover tracking: update highlighted row under cursor.
        # Only trust mouse_region_x/y when the event fired in the invoke region;
        # otherwise those coords are relative to a different region and could
        # spuriously hover items.
        if event.type == "MOUSEMOVE":
            from .common import event_in_invoke_region
            new_path = None
            if event_in_invoke_region(context, self._invoke_area_ptr, getattr(self, "_region", None)):
                try:
                    from ..ui.overlay import find_hit
                    hit = find_hit(event.mouse_region_x, event.mouse_region_y)
                except Exception:  # pylint: disable=broad-exception-caught
                    hit = None
                if hit and hit["kind"] == "script":
                    ref = hit["payload"].get("mapping_ref")
                    new_path = getattr(ref, "python_file", None) if ref is not None else None
            if new_path != self._hover_script_path:
                self._hover_script_path = new_path
                self._tag_redraw()
            return {"RUNNING_MODAL"}

        # LEFTMOUSE: plain click executes + closes; CTRL+click executes + stays open.
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            from .common import event_in_invoke_region
            if event_in_invoke_region(context, self._invoke_area_ptr, getattr(self, "_region", None)):
                try:
                    from ..ui.overlay import find_hit
                    hit = find_hit(event.mouse_region_x, event.mouse_region_y)
                except Exception:  # pylint: disable=broad-exception-caught
                    hit = None
                if hit and hit["kind"] == "script":
                    ref = hit["payload"].get("mapping_ref")
                    script_path = getattr(ref, "python_file", None) if ref is not None else None
                    script_label = getattr(ref, "label", "") if ref is not None else ""
                    if script_path:
                        chord_tokens = hit["payload"].get("chord_tokens") or []
                        chord_text = " ".join(chord_tokens) if chord_tokens else script_label
                        if event.ctrl:
                            # Stay open, just execute the script (no fade, no close).
                            self._execute_script_stay_open(context, script_path, script_label)
                            return {"RUNNING_MODAL"}
                        else:
                            self._finish(context)
                            self._show_fading_and_execute(context, chord_text, script_label, script_path)
                            return {"FINISHED"}
            return {"RUNNING_MODAL"}

        # Backspace to remove last character
        if event.type == "BACK_SPACE" and event.value == "PRESS":
            if self._text_buffer:
                self._text_buffer = self._text_buffer[:-1]
                self._invalidate_hit_boxes()
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
                    entry = self._filtered_scripts_list[idx]
                    script_name, script_path = entry.name, entry.path
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

        # Handle spacebar for text input (filtering with multiple words)
        elif event.type == "SPACE":
            self._text_buffer += " "
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        # Handle letter keys A-Z for text input (filtering)
        elif event.type in {chr(i) for i in range(ord('A'), ord('Z') + 1)}:
            # Convert to lowercase and add to text buffer
            char = event.type.lower()
            self._text_buffer += char
            self._invalidate_hit_boxes()
            self._tag_redraw()
            return {"RUNNING_MODAL"}

        return {"RUNNING_MODAL"}

    def _invalidate_hit_boxes(self):
        # Drop stale hit-boxes synchronously so a click arriving before the
        # next draw can't land on the old filtered list's rects.
        try:
            from ..ui.overlay import clear_hit_boxes
            clear_hit_boxes()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def _execute_script_stay_open(self, context, script_path, script_name):
        """Execute a script without closing the overlay (CTRL+click path).

        Skips the fading confirmation overlay and history write — the user
        stays in the scripts overlay and may fire more scripts in a row.
        """
        from ..utils.render import capture_viewport_context, validate_viewport_context, _execute_script_via_text_editor
        ctx_viewport = capture_viewport_context(context)

        def execute_delayed():
            try:
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                success, error_msg = _execute_script_via_text_editor(
                    script_path,
                    script_args={},
                    valid_ctx=valid_ctx,
                    context=bpy.context,
                )
                if not success:
                    print(f"Chord Song Scripts Overlay: {error_msg}")
                else:
                    print(f"Chord Song Scripts Overlay: Executed (stay open): {script_name}")
            except Exception:
                import traceback
                traceback.print_exc()
            return None

        bpy.app.timers.register(execute_delayed, first_interval=0.01)

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
                    print(f"Chord Song Scripts Overlay: Executed: {script_name}")

                    # Add script to history/recents after successful execution
                    # Don't include chord tokens for scripts in recents
                    add_to_history(
                        chord_tokens=[],
                        label=script_name,
                        icon=python_icon,
                        mapping_type="PYTHON_FILE",
                        python_file=script_path,
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

    def _restore_panels(self, context: bpy.types.Context):
        """Restore panels captured during invoke, then clear local state."""
        from ..utils.panels import restore_panels
        restore_panels(context, self._panel_states)
        self._panel_states = {}



