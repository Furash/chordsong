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

    def _draw_callback(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled:
            return

        try:
            import blf  # type: ignore
        except Exception:
            return

        # Resolve anchor & basic metrics
        region_w = context.region.width if context.region else 600
        region_h = context.region.height if context.region else 400
        
        # Get UI scale to properly scale fonts
        # blf.size() handles DPI automatically, but UI scale needs manual application
        try:
            ui_scale = getattr(context.preferences.view, "ui_scale", 1.0)
            dpi = context.preferences.system.dpi
            # Combine UI scale with DPI scaling (72 is standard DPI)
            scale_factor = ui_scale * (dpi / 72.0)
        except Exception:
            try:
                scale_factor = context.preferences.system.dpi / 72.0
            except Exception:
                scale_factor = 1.0
        
        # Scale offsets by scale factor
        pad_x = int(getattr(p, "overlay_offset_x", 14) * scale_factor)
        pad_y = int(getattr(p, "overlay_offset_y", 14) * scale_factor)

        # Compute candidates
        buffer_tokens = self._buffer or []
        cands = candidates_for_prefix(p.mappings, buffer_tokens)
        cands.sort(key=lambda c: (c.group.lower(), c.next_token))
        cands = cands[: p.overlay_max_items]

        prefix = " ".join(buffer_tokens) if buffer_tokens else "> ..."
        header = f"Chord Song  |  {prefix}"

        # Scale font sizes by scale factor (with larger defaults)
        header_size = int(getattr(p, "overlay_font_size_header", 16) * scale_factor)
        chord_size = int(getattr(p, "overlay_font_size_chord", 14) * scale_factor)
        body_size = int(getattr(p, "overlay_font_size_body", 12) * scale_factor)
        
        # Ensure minimum readable sizes
        header_size = max(header_size, 12)
        chord_size = max(chord_size, 11)
        body_size = max(body_size, 10)

        # Precompute layout widths for positioning (best effort)
        blf.size(0, header_size)
        header_w, header_h = blf.dimensions(0, header)

        # Footer hint shown as a final list item: "ESC - Cancel"
        esc_token = "ESC"
        esc_label = "Cancel"
        blf.size(0, chord_size)
        esc_w, _ = blf.dimensions(0, f"{esc_token:>4}")
        blf.size(0, body_size)
        esc_label_w, _esc_label_h = blf.dimensions(0, esc_label)

        # Scale spacing by DPI/UI scale as well
        gap = int(10 * scale_factor)
        col_gap = int(30 * scale_factor)
        line_h = int(body_size * 1.5)

        # Build display rows (group headers + items + footer).
        rows = []
        last_group = None
        for c in cands:
            if c.group and c.group != last_group:
                rows.append({"kind": "header", "text": f"[{c.group}]"})
                last_group = c.group
            rows.append({"kind": "item", "token": (c.next_token or "").upper(), "label": c.label})
        rows.append({"kind": "item", "token": "ESC", "label": "Cancel", "is_footer": True})

        # Wrap into columns by row count.
        max_rows = int(getattr(p, "overlay_column_rows", 12))
        if max_rows < 3:
            max_rows = 3

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

        # Compute column widths (token column + label column), include headers if wider.
        max_token_w = 0.0
        max_label_w = 0.0
        max_header_row_w = 0.0

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

        max_token_w = max(max_token_w, esc_w)
        max_label_w = max(max_label_w, esc_label_w)

        col_w = max(max_token_w + gap + max_label_w, max_header_row_w)
        num_cols = len(columns)
        block_w = max(header_w, num_cols * col_w + (num_cols - 1) * col_gap)

        max_rows_in_any = min(max_rows, max(len(c) for c in columns) if columns else 0)
        block_h = int(header_h + (line_h * (max_rows_in_any + 1)))

        pos = getattr(p, "overlay_position", "TOP_LEFT")
        if pos == "TOP_RIGHT":
            x = region_w - pad_x - block_w
            y = region_h - pad_y
        elif pos == "BOTTOM_LEFT":
            x = pad_x
            y = pad_y + block_h
        elif pos == "BOTTOM_RIGHT":
            x = region_w - pad_x - block_w
            y = pad_y + block_h
        else:  # TOP_LEFT
            x = pad_x
            y = region_h - pad_y

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

        # Render columns top-down, left-to-right.
        start_y = y
        for col_idx, col_rows in enumerate(columns):
            cx = x + col_idx * (col_w + col_gap)
            cy = start_y

            token_col_right_x = cx + max_token_w
            label_col_x = token_col_right_x + gap

            for r in col_rows:
                if r["kind"] == "header":
                    blf.size(0, body_size)
                    blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
                    blf.position(0, cx, cy, 0)
                    blf.draw(0, r["text"])
                    cy -= line_h
                    continue

                # item row
                token_txt = r["token"]
                label_txt = r["label"]

                blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
                blf.size(0, chord_size)
                tw, _ = blf.dimensions(0, token_txt)
                blf.position(0, token_col_right_x - tw, cy, 0)
                blf.draw(0, token_txt)

                blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
                blf.size(0, body_size)
                blf.position(0, label_col_x, cy, 0)
                blf.draw(0, label_txt)
                cy -= line_h

    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        p = prefs(context)
        p.ensure_defaults()

        self._buffer = []
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
                    opfn(call_ctx, **kwargs)
                except Exception:
                    pass
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


