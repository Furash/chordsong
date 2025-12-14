# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time

import bpy  # type: ignore

from ..core.engine import candidates_for_prefix, find_exact_mapping, normalize_token, parse_kwargs
from .common import prefs


class CHORDSONG_OT_Leader(bpy.types.Operator):
    """Start chord capture (leader)"""

    bl_idname = "chordsong.leader"
    bl_label = "Chord Song Leader"
    bl_options = {"REGISTER"}

    _timer = None
    _draw_handle = None
    _buffer = None
    _last_activity_time = 0.0
    _region = None
    _area = None
    _scroll_offset = 0

    def _add_timer(self, context: bpy.types.Context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

    def _remove_timer(self, context: bpy.types.Context):
        if self._timer is not None:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except Exception:
                pass
            self._timer = None

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

    def _calculate_scale_factor(self, context):
        """Calculate UI scale factor for fonts and spacing."""
        try:
            ui_scale = getattr(context.preferences.view, "ui_scale", 1.0)
            dpi = context.preferences.system.dpi
            return ui_scale * (dpi / 72.0)
        except Exception:
            try:
                return context.preferences.system.dpi / 72.0
            except Exception:
                return 1.0
    
    def _build_overlay_rows(self, cands, has_buffer):
        """Build display rows from candidates (group headers + items), footer returned separately."""
        rows = []
        last_group = None
        for c in cands:
            if c.group and c.group != last_group:
                rows.append({"kind": "header", "text": f"[{c.group}]"})
                last_group = c.group
            rows.append({"kind": "item", "token": (c.next_token or "").upper(), "label": c.label, "icon": c.icon})
        
        # Footer items (always at bottom)
        footer = []
        footer.append({"kind": "item", "token": "ESC", "label": "close", "icon": ""})
        if has_buffer:
            footer.append({"kind": "item", "token": "BS", "label": "go up a level", "icon": ""})
        
        return rows, footer
    
    def _wrap_into_columns(self, rows, max_rows):
        """Wrap rows into columns based on max_rows per column."""
        columns = [[]]
        for i, r in enumerate(rows):
            col = columns[-1]
            remaining = max_rows - len(col)
            if remaining <= 0:
                columns.append([])
                col = columns[-1]
                remaining = max_rows
            
            # Avoid a dangling header at the bottom of a column if possible.
            if r["kind"] == "header" and remaining == 1 and i + 1 < len(rows):
                columns.append([])
                col = columns[-1]
            
            col.append(r)
        return columns
    
    def _calculate_column_widths(self, columns, footer, chord_size, body_size):
        """Calculate maximum token and label widths across all columns and footer."""
        import blf  # type: ignore
        
        max_token_w = 0.0
        max_label_w = 0.0
        max_header_row_w = 0.0
        
        # Check all columns
        for col in columns:
            for r in col:
                if r["kind"] == "header":
                    blf.size(0, body_size)
                    w, _ = blf.dimensions(0, r["text"])
                    max_header_row_w = max(max_header_row_w, w)
                else:
                    blf.size(0, chord_size)
                    tw, _ = blf.dimensions(0, r["token"])
                    max_token_w = max(max_token_w, tw)
                    blf.size(0, body_size)
                    lw, _ = blf.dimensions(0, r["label"])
                    max_label_w = max(max_label_w, lw)
        
        # Check footer items
        for r in footer:
            blf.size(0, chord_size)
            tw, _ = blf.dimensions(0, r["token"])
            max_token_w = max(max_token_w, tw)
            blf.size(0, body_size)
            lw, _ = blf.dimensions(0, r["label"])
            max_label_w = max(max_label_w, lw)
        
        return max_token_w, max_label_w, max_header_row_w
    
    def _calculate_overlay_position(self, p, region_w, region_h, block_w, block_h, pad_x, pad_y):
        """Calculate overlay position based on anchor setting."""
        pos = getattr(p, "overlay_position", "TOP_LEFT")
        if pos == "TOP_RIGHT":
            return region_w - pad_x - block_w, region_h - pad_y
        elif pos == "BOTTOM_LEFT":
            return pad_x, pad_y + block_h
        elif pos == "BOTTOM_RIGHT":
            return region_w - pad_x - block_w, pad_y + block_h
        else:  # TOP_LEFT
            return pad_x, region_h - pad_y
    
    def _render_overlay(self, context, p, columns, footer, x, y, header, header_size, chord_size, body_size, 
                       max_token_w, gap, col_w, col_gap, line_h, icon_size):
        """Render the overlay at the calculated position."""
        import blf  # type: ignore
        import gpu  # type: ignore
        from gpu_extras.batch import batch_for_shader  # type: ignore
        
        # Colors
        col_header = getattr(p, "overlay_color_header", (1.0, 1.0, 1.0, 1.0))
        col_chord = getattr(p, "overlay_color_chord", (0.65, 0.8, 1.0, 1.0))
        col_label = getattr(p, "overlay_color_label", (1.0, 1.0, 1.0, 1.0))
        
        # Header
        blf.size(0, header_size)
        blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
        blf.position(0, x, y, 0)
        blf.draw(0, header)
        y -= int(header_size * 1.6)
        
        # Render columns top-down, left-to-right
        start_y = y
        for col_idx, col_rows in enumerate(columns):
            cx = x + col_idx * (col_w + col_gap)
            cy = start_y
            
            # Icon, arrow, token, label layout
            icon_x = cx
            arrow_x = icon_x + icon_size + gap // 2
            token_col_right_x = arrow_x + gap + max_token_w
            label_col_x = token_col_right_x + gap
            
            for r in col_rows:
                if r["kind"] == "header":
                    blf.size(0, body_size)
                    blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
                    blf.position(0, icon_x, cy, 0)
                    blf.draw(0, r["text"])
                    cy -= line_h
                    continue
                
                # item row
                token_txt = r["token"]
                label_txt = r["label"]
                icon_name = r.get("icon", "")
                
                # Draw icon if present
                if icon_name:
                    try:
                        self._draw_icon(context, icon_name, icon_x, cy, icon_size)
                    except Exception:
                        pass
                
                # Draw arrow
                blf.size(0, body_size)
                blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * 0.5)
                blf.position(0, arrow_x, cy, 0)
                blf.draw(0, "→")
                
                # Draw token (right-aligned)
                blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
                blf.size(0, chord_size)
                tw, _ = blf.dimensions(0, token_txt)
                blf.position(0, token_col_right_x - tw, cy, 0)
                blf.draw(0, token_txt)
                
                # Draw label
                blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
                blf.size(0, body_size)
                blf.position(0, label_col_x, cy, 0)
                blf.draw(0, label_txt)
                cy -= line_h
        
        # Render footer at the bottom
        if footer:
            # Add spacing before footer
            footer_y = start_y - (len(columns[0]) * line_h if columns and columns[0] else 0) - int(line_h * 0.5)
            
            # Calculate footer width to span all columns
            footer_x = x
            
            icon_x = footer_x
            arrow_x = icon_x + icon_size + gap // 2
            token_col_right_x = arrow_x + gap + max_token_w
            label_col_x = token_col_right_x + gap
            
            for r in footer:
                token_txt = r["token"]
                label_txt = r["label"]
                
                # Draw token in angle brackets
                blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
                blf.size(0, chord_size)
                display_token = f"<{token_txt.lower()}>"
                tw, _ = blf.dimensions(0, display_token)
                blf.position(0, token_col_right_x - tw, footer_y, 0)
                blf.draw(0, display_token)
                
                # Draw label
                blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
                blf.size(0, body_size)
                blf.position(0, label_col_x, footer_y, 0)
                blf.draw(0, label_txt)
                
                # Move to next column for next footer item
                footer_x += col_w + col_gap
                icon_x = footer_x
                arrow_x = icon_x + icon_size + gap // 2
                token_col_right_x = arrow_x + gap + max_token_w
                label_col_x = token_col_right_x + gap
    
    def _draw_icon(self, context, icon_name, x, y, size):
        """Draw a Blender icon at the specified position."""
        import bpy
        import gpu
        from gpu_extras.batch import batch_for_shader
        
        # Get the icon
        try:
            icon_id = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items[icon_name].value
        except (KeyError, AttributeError):
            return
        
        # Icons are drawn using the theme icon texture
        # This is a simplified approach - just draw a colored square for now
        # Full icon support would require accessing the icon atlas texture
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        
        # Draw a small colored indicator
        vertices = (
            (x, y), (x + size, y),
            (x + size, y + size), (x, y + size)
        )
        
        indices = ((0, 1, 2), (0, 2, 3))
        
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        
        # Use a muted color for the icon placeholder
        shader.uniform_float("color", (0.5, 0.7, 0.9, 0.8))
        
        gpu.state.blend_set('ALPHA')
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    def _draw_callback(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled:
            return

        try:
            import blf  # type: ignore
        except Exception:
            return

        # Basic metrics
        region_w = context.region.width if context.region else 600
        region_h = context.region.height if context.region else 400
        
        scale_factor = self._calculate_scale_factor(context)
        pad_x = int(getattr(p, "overlay_offset_x", 14) * scale_factor)
        pad_y = int(getattr(p, "overlay_offset_y", 14) * scale_factor)

        # Compute candidates
        buffer_tokens = self._buffer or []
        cands = candidates_for_prefix(p.mappings, buffer_tokens)
        cands.sort(key=lambda c: (c.group.lower(), c.next_token))
        cands = cands[: p.overlay_max_items]

        # Display buffer with + separator instead of spaces
        prefix = "+".join(buffer_tokens) if buffer_tokens else "> ..."
        header = f"Chord Song  |  {prefix}"

        # Scale font sizes
        header_size = max(int(getattr(p, "overlay_font_size_header", 16) * scale_factor), 12)
        chord_size = max(int(getattr(p, "overlay_font_size_chord", 14) * scale_factor), 11)
        body_size = max(int(getattr(p, "overlay_font_size_body", 12) * scale_factor), 10)
        icon_size = int(body_size * 1.2)

        # Precompute layout dimensions
        blf.size(0, header_size)
        header_w, header_h = blf.dimensions(0, header)

        # Scale spacing
        gap = int(10 * scale_factor)
        col_gap = int(30 * scale_factor)
        line_h = int(body_size * 1.5)

        # Build rows and footer
        rows, footer = self._build_overlay_rows(cands, bool(buffer_tokens))
        max_rows = max(int(getattr(p, "overlay_column_rows", 12)), 3)
        columns = self._wrap_into_columns(rows, max_rows)

        # Calculate dimensions (including icon space and footer)
        max_token_w, max_label_w, max_header_row_w = self._calculate_column_widths(columns, footer, chord_size, body_size)
        
        # Account for icon and arrow in column width
        arrow_w = gap
        col_w = max(icon_size + gap + arrow_w + max_token_w + gap + max_label_w, max_header_row_w)
        
        num_cols = len(columns)
        block_w = max(header_w, num_cols * col_w + (num_cols - 1) * col_gap)
        max_rows_in_any = min(max_rows, max(len(c) for c in columns) if columns else 0)
        
        # Add extra space for footer
        footer_rows = 1 if footer else 0
        block_h = int(header_h + (line_h * (max_rows_in_any + footer_rows + 2)))

        # Calculate position
        x, y = self._calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y)

        # Render
        self._render_overlay(context, p, columns, footer, x, y, header, header_size, chord_size, body_size,
                           max_token_w, gap, col_w, col_gap, line_h, icon_size)

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
        self._scroll_offset = 0
        self._last_activity_time = time.monotonic()

        self._ensure_draw_handler(context)
        self._add_timer(context)
        self._tag_redraw()
        return {"RUNNING_MODAL"}

    def _finish(self, context: bpy.types.Context):
        self._remove_timer(context)
        self._remove_draw_handler()
        self._tag_redraw()

    def cancel(self, context: bpy.types.Context):
        """
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
                self._last_activity_time = time.monotonic()
                self._tag_redraw()
                return {"RUNNING_MODAL"}
            else:
                # No buffer, treat as cancel
                self._finish(context)
                return {"CANCELLED"}

        # Timeout (driven by TIMER events)
        if event.type == "TIMER":
            if p.timeout_ms > 0:
                if (time.monotonic() - self._last_activity_time) * 1000.0 > p.timeout_ms:
                    self._finish(context)
                    return {"CANCELLED"}
            return {"RUNNING_MODAL"}

        if event.value != "PRESS":
            return {"RUNNING_MODAL"}

        tok = normalize_token(event.type)
        if tok is None:
            return {"RUNNING_MODAL"}

        self._buffer.append(tok)
        self._scroll_offset = 0  # Reset scroll when adding to buffer
        self._last_activity_time = time.monotonic()

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
            
            # Capture full context for context-sensitive operators (e.g., view3d.view_all)
            # Store the current context as a copy to use later
            ctx = context.copy()
            
            # Finish the modal operator FIRST to ensure clean state before calling other operators
            # This prevents blocking issues when opening preferences or other UI operations
            self._finish(context)
            
            # Defer operator execution to next frame using a timer
            # This ensures the modal operator fully finishes before the next operator runs
            def execute_operator_delayed():
                try:
                    mod_name, fn_name = op.split(".", 1)
                    opmod = getattr(bpy.ops, mod_name)
                    opfn = getattr(opmod, fn_name)
                    
                    # Use temp_override for Blender 4.0+ context override
                    # This is the proper way to provide context to operators
                    with bpy.context.temp_override(**ctx):
                        opfn(call_ctx, **kwargs)
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


