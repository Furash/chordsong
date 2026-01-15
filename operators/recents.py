"""Recents operator for displaying and executing recent chord invocations."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

from ..core.history import get_history
from ..core.engine import (
    normalize_token,
    get_leader_key_type,
    get_leader_key_token,
)
from ..utils.render import (
    DrawHandlerManager,
    calculate_scale_factor,
    calculate_overlay_position,
    capture_viewport_context,
    execute_history_entry_operator,
    execute_history_entry_script,
    execute_history_entry_toggle,
    execute_history_entry_property,
)
from .common import prefs

def _create_context_wrapper(ctx_viewport):
    """Create a context wrapper with captured viewport context."""
    class ContextWrapper:
        def __init__(self, ctx_viewport):
            self._ctx_viewport = ctx_viewport
        def __getattr__(self, name):
            if name in self._ctx_viewport:
                return self._ctx_viewport[name]
            return getattr(bpy.context, name)

    return ContextWrapper(ctx_viewport) if ctx_viewport else bpy.context

class CHORDSONG_OT_Recents(bpy.types.Operator):
    """Show recent chord invocations and execute selected one"""

    bl_idname = "chordsong.recents"
    bl_label = "Chord Song Recents"
    bl_options = {"REGISTER"}

    _buffer = None  # Buffer for capturing digits
    _draw_manager = None  # DrawHandlerManager instance

    def _draw_callback(self):
        """Draw callback for the recents overlay."""
        try:
            # Check if self is still valid (operator not removed during addon disable)
            try:
                _ = self.bl_idname
            except ReferenceError:
                # Operator has been removed, stop drawing
                return

            p = prefs(bpy.context)
        except (KeyError, AttributeError):
            # Addon is being disabled/unregistered, preferences no longer available
            return
        if not p.overlay_enabled:
            return

        # Get history
        history = get_history()
        entries = history.get_all()

        # Draw the recents overlay
        self._draw_recents_overlay(bpy.context, p, entries, self._buffer or [])

    def _draw_recents_overlay(self, context, p, entries, buffer_digits):
        """Draw the recents overlay showing numbered list."""
        from ..ui.overlay.render import (
            draw_overlay_header,
            draw_list_background,
            draw_overlay_footer,
            draw_icon,
            linear_to_srgb
        )

        try:
            import blf  # type: ignore
        except Exception:
            return

        # Basic metrics
        region_w = context.region.width if context.region else 600
        region_h = context.region.height if context.region else 400

        # Calculate scale factor
        scale_factor = calculate_scale_factor(context)

        # Font sizes
        header_size = max(int(p.overlay_font_size_header * scale_factor), 12)
        chord_size = max(int(p.overlay_font_size_chord * scale_factor), 11)
        body_size = max(int(p.overlay_font_size_body * scale_factor), 10)
        icon_size = chord_size

        # Colors (convert from linear to sRGB to match picker preview)
        col_header = linear_to_srgb(p.overlay_color_header)
        col_chord = linear_to_srgb(p.overlay_color_chord)
        col_label = linear_to_srgb(p.overlay_color_label)
        col_icon = linear_to_srgb(p.overlay_color_icon)
        col_recents_hotkey = linear_to_srgb(p.overlay_color_recents_hotkey)

        # Helper to convert index to hotkey (1-9, a-z, A-Z, !-, -=+, punctuation)
        def index_to_hotkey(idx):
            if idx < 9:
                return str(idx + 1)  # 1-9
            elif idx < 35:  # 9 + 26
                return chr(ord('a') + (idx - 9))  # a-z for items 10-35
            elif idx < 61:  # 35 + 26
                char = chr(ord('a') + (idx - 35))
                return f"+{char}" # +a-+z for items 36-61
            elif idx < 71:  # 61-70 (10 items)
                # +1-+0 for items 62-71
                shifted = ["+1", "+2", "+3", "+4", "+5", "+6", "+7", "+8", "+9", "+0"]
                shift_idx = idx - 61
                return shifted[shift_idx] if shift_idx < len(shifted) else "?"
            elif idx < 74:  # 71-73 (3 items)
                # - = + for items 72-74 (careful: + is shifted =)
                extra = ["-", "=", "+="]
                extra_idx = idx - 71
                return extra[extra_idx] if extra_idx < len(extra) else "?"
            else:  # 74-87 (14 items)
                # ` ~ , . < > : ; ' " [ ] { }
                punctuation = ["grave", "+grave", ",", ".", "+,", "+.", "+;", ";", "'", "+'", "[", "]", "+[", "+]"]
                punct_idx = idx - 74
                return punctuation[punct_idx] if punct_idx < len(punctuation) else "?"

        # Build header
        num_entries = len(entries)
        if num_entries == 0:
            header = "Recents  |  No history yet"
        elif num_entries <= 9:
            header = f"Recents  |  Press 1-{num_entries} to execute"
        elif num_entries <= 35:  # 9 + 26 lowercase
            last_key = index_to_hotkey(num_entries-1)
            header = f"Recents  |  Press 1-9, a-{last_key} to execute"
        elif num_entries <= 61:  # 35 + 26 uppercase
            last_key = index_to_hotkey(num_entries-1)
            header = f"Recents  |  Press 1-9, a-z, A-{last_key} to execute"
        elif num_entries <= 71:  # 61 + 10 shifted
            last_key = index_to_hotkey(num_entries-1)
            header = f"Recents  |  Press 1-9, a-z, +a-+z, +1-{last_key} to execute"
        elif num_entries <= 74:  # 71 + 3 extra
            last_key = index_to_hotkey(num_entries-1)
            header = f"Recents  |  Press 1-9, a-z, +a-+z, +1-+0, -/=/+= to execute"
        else:
            header = f"Recents  |  Press any hotkey (showing {min(88, p.overlay_max_items)})"

        # Measure header
        blf.size(0, header_size)
        header_w, header_h = blf.dimensions(0, header)

        # Calculate layout (using preferences)
        gap = int(p.overlay_gap * scale_factor)
        line_h = int(body_size * p.overlay_line_height)
        pad_x = int(p.overlay_offset_x * scale_factor)
        pad_y = int(p.overlay_offset_y * scale_factor)

        # Show all entries up to the configured max_items (capped at 88: 9 + 26. + 26 + 10 + 3 + 14)
        max_items = min(p.overlay_max_items, len(entries), 88)
        visible_entries = entries[:max_items]

        # Calculate column layout
        column_rows = p.overlay_column_rows
        num_columns = (max_items + column_rows - 1) // column_rows  # Ceiling division

        # Calculate column widths
        blf.size(0, chord_size)
        max_hotkey_w = 0.0
        max_icon_w = 0.0
        max_chord_w = 0.0
        max_label_w = 0.0
        has_any_icon = False

        for i, entry in enumerate(visible_entries):
            # Hotkey width (1-9, a-z)
            hotkey_text = index_to_hotkey(i)
            hw, _ = blf.dimensions(0, hotkey_text)
            max_hotkey_w = max(max_hotkey_w, hw)

            # Icon width
            if entry.icon:
                has_any_icon = True
                iw, _ = blf.dimensions(0, entry.icon)
                max_icon_w = max(max_icon_w, iw)

            # Chord width
            chord_text = "+".join(entry.chord_tokens)
            cw, _ = blf.dimensions(0, chord_text)
            max_chord_w = max(max_chord_w, cw)

            # Label width
            blf.size(0, body_size)
            lw, _ = blf.dimensions(0, entry.label)
            max_label_w = max(max_label_w, lw)
            blf.size(0, chord_size)

        # Calculate positions
        col_spacing = int(30 * scale_factor)
        icon_part_w = (max_icon_w + gap) if has_any_icon else 0
        col_w = max_hotkey_w + gap + icon_part_w + max_chord_w + gap + max_label_w
        block_w = max(header_w, col_w * num_columns + col_spacing * (num_columns - 1))
        items_per_column = min(column_rows, max_items)
        block_h = int(header_h + (line_h * (items_per_column + 3)))

        # Position (matching main overlay)
        x, y = calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y)

        # 1. Draw Header
        current_y, header_bg_bottom = draw_overlay_header(p, region_w, y, header, header_size, body_size, chord_size, header_w)

        # 2. Draw Footer & List Background
        # Calculate from current_y (bottom of header) not y (top of header)
        footer_y = current_y - (items_per_column * line_h) - chord_size

        # Determine footer visibility and position
        footer_bg_top = footer_y + chord_size # Default if no footer

        if p.overlay_show_footer:
            leader_token = get_leader_key_token()
            footer_items = [
                {"token": "ESC", "label": "Close", "icon": ""},
                {"token": leader_token, "label": "Repeat Most Recent", "icon": ""}
            ]

            # Use prefs for footer text size
            footer_text_size_base = getattr(p, "overlay_font_size_footer", 12)
            footer_text_size = max(int(footer_text_size_base * scale_factor), 10)

            # We need mock max_token_w/max_label_w for footer spacing calculation
            blf.size(0, footer_text_size)
            f_token_w = 0.0
            f_label_w = 0.0
            for item in footer_items:
                tw, _ = blf.dimensions(0, f"<{item['token'].upper()}>")
                f_token_w = max(f_token_w, tw)
                blf.size(0, body_size)
                lw, _ = blf.dimensions(0, item["label"])
                f_label_w = max(f_label_w, lw)
                blf.size(0, footer_text_size)

            footer_bg_top = draw_overlay_footer(
                p, region_w, footer_y, footer_items, footer_text_size, footer_text_size, scale_factor,
                icon_size, f_token_w, f_label_w
            )
        else:
            # If no footer, align list bg bottom with the end of list content
            # (or block bottom). We can reuse footer_y logic but adjust slightly.
             # Actually, if no footer, we want the list background to end where the content ends
             # items_per_column * line_h gives the height.
             footer_bg_top = current_y - (items_per_column * line_h) - (chord_size * 0.5)

        draw_list_background(p, region_w, header_bg_bottom, footer_bg_top)

        # 3. Draw Columns
        # Use current_y from header return
        # start_y calculation in recents was originally:
        # y -= int(header_size / 2 + text_height * 0.75 + chord_size)
        # which matches draw_overlay_header return value

        current_y = current_y
        current_column = 0
        column_x = x

        for i, entry in enumerate(visible_entries):
            # Check if we need to start a new column
            if i > 0 and i % column_rows == 0:
                current_column += 1
                column_x = x + current_column * (col_w + col_spacing)
                current_y = y - int(header_size / 2 + (max(header_size, body_size) * 1.3) * 0.75 + chord_size) # Reset to top of column

            # Column positions
            hotkey_col_x = column_x
            icon_col_x = column_x + max_hotkey_w + gap
            chord_col_x = icon_col_x + icon_part_w
            label_col_x = chord_col_x + max_chord_w + gap

            # Draw hotkey (1-9, a-z)
            hotkey_text = index_to_hotkey(i)
            blf.size(0, chord_size)
            blf.color(0, col_recents_hotkey[0], col_recents_hotkey[1], col_recents_hotkey[2], col_recents_hotkey[3])
            blf.position(0, hotkey_col_x, current_y, 0)
            blf.draw(0, hotkey_text)

            # For scripts (PYTHON_FILE), draw icon in icon column and skip chord
            is_script = entry.mapping_type == "PYTHON_FILE"
            
            if is_script:
                # Draw Python icon in icon column (aligned with other icons)
                if entry.icon:
                    try:
                        blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                        draw_icon(entry.icon, icon_col_x, current_y, icon_size)
                    except Exception:
                        pass
                # Skip chord for scripts, label starts after icon column
                label_start_x = icon_col_x + icon_part_w
            else:
                # Draw icon if present (50% alpha)
                if entry.icon:
                    try:
                        blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3] * 0.25)
                        draw_icon(entry.icon, icon_col_x, current_y, icon_size)
                    except Exception:
                        pass

                # Draw chord (50% alpha)
                chord_text = "+".join(entry.chord_tokens)
                blf.size(0, chord_size)
                blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3] * 0.25)
                blf.position(0, chord_col_x, current_y, 0)
                blf.draw(0, chord_text)
                
                label_start_x = label_col_x

            # Draw label
            blf.size(0, body_size)
            blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
            blf.position(0, label_start_x, current_y, 0)
            blf.draw(0, entry.label)

            current_y -= line_h

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start recents modal operation."""
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
        self._draw_manager = DrawHandlerManager()
        self._draw_manager.ensure_handler(context, self._draw_callback, p)

        context.window_manager.modal_handler_add(self)
        self._draw_manager.tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        if self._draw_manager:
            self._draw_manager.remove_handler()
            self._draw_manager.tag_redraw()
            self._draw_manager = None

    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted."""
        self._finish(context)

    def _execute_history_entry(self, context, entry):
        """Execute a history entry."""
        from ..operators.leader import _show_fading_overlay

        # Capture viewport context BEFORE finishing modal (when we have valid context)
        ctx_viewport = capture_viewport_context(context)

        # Finish modal before executing
        self._finish(context)

        # Execute based on mapping type
        if entry.mapping_type == "OPERATOR":
            def execute_operator_delayed():
                # Validate context before using it (may be invalid after undo)
                from ..utils.render import validate_viewport_context
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                ctx_wrapper = _create_context_wrapper(valid_ctx)
                success, error_msg = execute_history_entry_operator(ctx_wrapper, entry)
                if success:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, entry.label, entry.icon)
                elif error_msg:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, error_msg, "CANCEL")
                return None

            bpy.app.timers.register(execute_operator_delayed, first_interval=0.01)

        elif entry.mapping_type == "PYTHON_FILE":
            def execute_script_delayed():
                # Validate context before using it (may be invalid after undo)
                from ..utils.render import validate_viewport_context
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                ctx_wrapper = _create_context_wrapper(valid_ctx)
                success, error_msg = execute_history_entry_script(ctx_wrapper, entry)
                if success:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, entry.label, entry.icon)
                elif error_msg:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, error_msg, "CANCEL")
                return None

            bpy.app.timers.register(execute_script_delayed, first_interval=0.01)

        elif entry.mapping_type == "CONTEXT_TOGGLE":
            def execute_toggle_delayed():
                # Validate context before using it (may be invalid after undo)
                from ..utils.render import validate_viewport_context
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                ctx_wrapper = _create_context_wrapper(valid_ctx)
                success, result = execute_history_entry_toggle(ctx_wrapper, entry)
                if success and result is not None:
                    status = "ON" if result else "OFF"
                    _show_fading_overlay(bpy.context, entry.chord_tokens, f"{entry.label} ({status})", entry.icon)
                elif not success and isinstance(result, str):
                    _show_fading_overlay(bpy.context, entry.chord_tokens, result, "CANCEL")
                return None

            bpy.app.timers.register(execute_toggle_delayed, first_interval=0.01)

        elif entry.mapping_type == "CONTEXT_PROPERTY":
            def execute_property_delayed():
                # Validate context before using it (may be invalid after undo)
                from ..utils.render import validate_viewport_context
                valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None
                ctx_wrapper = _create_context_wrapper(valid_ctx)
                success, error_msg = execute_history_entry_property(ctx_wrapper, entry)
                if success:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, f"{entry.label}: {entry.property_value}", entry.icon)
                elif error_msg:
                    _show_fading_overlay(bpy.context, entry.chord_tokens, error_msg, "CANCEL")
                return None

            bpy.app.timers.register(execute_property_delayed, first_interval=0.01)

    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        history = get_history()

        # Cancel keys
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        # Check for leader key to repeat most recent
        leader_key = get_leader_key_type()
        if event.type == leader_key:
            entry = history.get(0)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, "No history entry to repeat")
                self._finish(context)
                return {"CANCELLED"}

        # Check for digit input (1-9 only, immediate execution)
        tok = normalize_token(event.type, shift=event.shift, ctrl=event.ctrl, alt=event.alt, oskey=event.oskey)
        if tok and tok.isdigit():
            try:
                number = int(tok)
                if 1 <= number <= 9:
                    entry = history.get(number - 1)  # Convert to 0-based index
                    if entry:
                        self._execute_history_entry(context, entry)
                        return {"FINISHED"}
                    else:
                        self.report({"WARNING"}, f"No history entry #{number}")
                        self._finish(context)
                        return {"CANCELLED"}
            except ValueError:
                pass

        # Handle lowercase letter keys (a-z for items 10-35)
        if tok and len(tok) == 1 and tok.isalpha() and tok.islower():
            # a=10th item (index 9), b=11th (index 10), etc.
            index = ord(tok) - ord('a') + 9
            entry = history.get(index)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, f"No history entry at position '{tok}'")
                self._finish(context)
                return {"CANCELLED"}

        # Handle uppercase letter keys (A-Z for items 36-61)
        if tok and tok.startswith('+') and len(tok) == 2 and tok[1].isalpha():
            # +a=36th item (index 35), +b=37th (index 36), etc.
            index = ord(tok[1]) - ord('a') + 35
            entry = history.get(index)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, f"No history entry at position '{tok}'")
                self._finish(context)
                return {"CANCELLED"}

        # Handle shifted number keys (+1-+0 for items 62-71)
        shifted_map = {"+1": 61, "+2": 62, "+3": 63, "+4": 64, "+5": 65, "+6": 66, "+7": 67, "+8": 68, "+9": 69, "+0": 70}
        if tok in shifted_map:
            index = shifted_map[tok]
            entry = history.get(index)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, f"No history entry at position '{tok}'")
                self._finish(context)
                return {"CANCELLED"}

        # Handle extra keys (- = += for items 72-74)
        extra_map = {"-": 71, "=": 72, "+=": 73}
        if tok in extra_map:
            index = extra_map[tok]
            entry = history.get(index)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, f"No history entry at position '{tok}'")
                self._finish(context)
                return {"CANCELLED"}

        # Handle punctuation keys (grave, +grave ... for items 75-88)
        punct_map = {
            "grave": 74, "+grave": 75, ",": 76, ".": 77,
            "+,": 78, "+.": 79, "+;": 80, ";": 81,
            "'": 82, "+'": 83, "[": 84, "]": 85,
            "+[": 86, "+]": 87
        }
        if tok in punct_map:
            index = punct_map[tok]
            entry = history.get(index)
            if entry:
                self._execute_history_entry(context, entry)
                return {"FINISHED"}
            else:
                self.report({"WARNING"}, f"No history entry at position '{tok}'")
                self._finish(context)
                return {"CANCELLED"}

        # Unknown key, ignore
        return {"RUNNING_MODAL"}
