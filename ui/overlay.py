"""Overlay rendering for chord capture display."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
from ..core.engine import candidates_for_prefix

# Import gpu modules at module level for better performance
import gpu  # type: ignore
from gpu_extras.batch import batch_for_shader  # type: ignore


def get_last_chord_state():
    """Get the last chord state from the leader module."""
    try:
        from ..operators import leader
        return leader._last_chord_state  # pylint: disable=protected-access
    except Exception:
        return None


# Cache for overlay layout to avoid recalculating every frame
_overlay_cache = {
    "buffer_tokens": None,
    "prefs_hash": None,
    "layout_data": None,
}


def clear_overlay_cache():
    """Clear the overlay cache. Call when mappings are updated."""
    _overlay_cache["buffer_tokens"] = None
    _overlay_cache["prefs_hash"] = None
    _overlay_cache["layout_data"] = None


def calculate_scale_factor(context):
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


def get_prefs_hash(p, region_w, region_h):
    """Get a hash of preferences that affect overlay layout."""
    return (
        p.overlay_font_size_header,
        p.overlay_font_size_chord,
        p.overlay_font_size_body,
        p.overlay_column_rows,
        p.overlay_max_items,
        p.overlay_offset_x,
        p.overlay_offset_y,
        p.overlay_position,
        region_w,
        region_h,
    )


def build_overlay_rows(cands, has_buffer):
    """Build display rows from candidates, footer returned separately."""
    # Group candidates by next token to detect multi-chord prefixes
    token_groups = {}
    for c in cands:
        token = c.next_token
        if token not in token_groups:
            token_groups[token] = []
        token_groups[token].append(c)
    
    rows = []
    for token, group in sorted(token_groups.items()):
        # Use first icon if available, or empty string
        icon = group[0].icon if group[0].icon else ""
        
        # Check if any candidate in this group is non-final (intermediate level)
        has_non_final = any(not c.is_final for c in group)
        
        if has_non_final:
            # Intermediate chord level - show group name instead of label
            # Check if all items in this group have the same group name
            group_names = {c.group for c in group if c.group}
            if len(group_names) == 1:
                # All belong to the same group, use group name
                label = f"{list(group_names)[0]}..."
            else:
                # Mixed groups or no group, use generic label
                label = "More..."
            
            rows.append({"kind": "item", "token": token.upper(), "label": label, "icon": icon})
        elif len(group) > 1:
            # Multiple final chords share this prefix, show a summary
            # Check if all items in this group have the same group name
            group_names = {c.group for c in group if c.group}
            if len(group_names) == 1:
                # All belong to the same group, use group name
                label = f"{list(group_names)[0]}..."
            else:
                # Mixed groups or no group, use first label's first word
                label = f"{group[0].label.split()[0] if group[0].label else 'More'}..."
            
            rows.append({"kind": "item", "token": token.upper(), "label": label, "icon": icon})
        else:
            # Single final chord, show its label
            c = group[0]
            rows.append({"kind": "item", "token": (c.next_token or "").upper(), "label": c.label, "icon": c.icon})

    # Footer items (always at bottom)
    footer = []
    if not has_buffer:
        # Only show repeat option at root level (no buffer)
        last_chord = get_last_chord_state()
        if last_chord and (last_chord.get("operator") or last_chord.get("python_file")):
            # Show last chord's label and icon
            last_label = last_chord.get("label") or "Last Chord"
            last_icon = last_chord.get("icon") or ""
            footer.append({"kind": "item", "token": "SPACE", "label": last_label, "icon": last_icon})
        else:
            # No previous chord to repeat
            footer.append({"kind": "item", "token": "SPACE", "label": "Repeat Last Chord", "icon": ""})
    footer.append({"kind": "item", "token": "ESC", "label": "Close", "icon": ""})
    if has_buffer:
        footer.append({"kind": "item", "token": "BS", "label": "Back", "icon": ""})

    return rows, footer


def wrap_into_columns(rows, max_rows):
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


def calculate_column_widths(columns, footer, chord_size, body_size):
    """Calculate maximum token and label widths across all columns and footer."""
    import blf  # type: ignore

    max_token_w = 0.0
    max_label_w = 0.0
    max_header_row_w = 0.0

    # Set font sizes once
    blf.size(0, chord_size)
    
    # Check all columns
    for col in columns:
        for r in col:
            if r["kind"] == "header":
                blf.size(0, body_size)
                w, _ = blf.dimensions(0, r["text"])
                max_header_row_w = max(max_header_row_w, w)
                blf.size(0, chord_size)  # Reset to chord size
            else:
                # Token width (already at chord_size)
                tw, _ = blf.dimensions(0, r["token"])
                max_token_w = max(max_token_w, tw)
                
                # Label width
                blf.size(0, body_size)
                lw, _ = blf.dimensions(0, r["label"])
                max_label_w = max(max_label_w, lw)
                blf.size(0, chord_size)  # Reset to chord size

    # Check footer items (already at chord_size)
    for r in footer:
        tw, _ = blf.dimensions(0, r["token"])
        max_token_w = max(max_token_w, tw)
        
        blf.size(0, body_size)
        lw, _ = blf.dimensions(0, r["label"])
        max_label_w = max(max_label_w, lw)
        blf.size(0, chord_size)  # Reset to chord size

    return max_token_w, max_label_w, max_header_row_w


def calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y):
    """Calculate overlay position based on anchor setting."""
    pos = p.overlay_position
    if pos == "TOP_RIGHT":
        return region_w - pad_x - block_w, region_h - pad_y
    elif pos == "BOTTOM_LEFT":
        return pad_x, pad_y + block_h
    elif pos == "BOTTOM_RIGHT":
        return region_w - pad_x - block_w, pad_y + block_h
    else:  # TOP_LEFT
        return pad_x, region_h - pad_y


def draw_icon(icon_text, x, y, size):
    """Draw a Nerd Fonts icon/emoji at the specified position."""
    if not icon_text:
        return

    import blf  # type: ignore

    # Draw the icon as text using the current font
    blf.size(0, size)
    blf.position(0, x, y, 0)
    blf.draw(0, icon_text)


def render_overlay(_context, p, columns, footer, x, y, header, header_size, chord_size, body_size,
                   max_token_w, gap, col_w, col_gap, line_h, icon_size, block_w, max_label_w, region_w, header_w):
    """Render the overlay at the calculated position."""
    import blf  # type: ignore

    # Colors
    col_header = p.overlay_color_header
    col_chord = p.overlay_color_chord
    col_label = p.overlay_color_label
    col_icon = p.overlay_color_icon

    # Header with full-width background
    # Calculate header background dimensions
    text_center_y = y + (header_size / 2)
    text_height = max(header_size, body_size) * 1.3
    
    # Full width background
    bg_x1 = 0
    bg_x2 = region_w
    
    # Vertically centered around text
    bg_y1 = text_center_y - (text_height * 0.75)
    bg_y2 = text_center_y + (text_height * 0.45)
    
    # Enable GPU blending for transparency
    gpu.state.blend_set('ALPHA')
    
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    vertices = (
        (bg_x1, bg_y1),
        (bg_x2, bg_y1),
        (bg_x2, bg_y2),
        (bg_x1, bg_y2),
    )
    indices = ((0, 1, 2), (0, 2, 3))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, 0.35))
    batch.draw(shader)
    
    # Restore default blending
    gpu.state.blend_set('NONE')
    
    # Center header text
    header_x = (region_w - header_w) // 2
    blf.size(0, header_size)
    blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
    blf.position(0, header_x, y, 0)
    blf.draw(0, header)
    # Account for background extension when calculating spacing
    y -= int(header_size / 2 + text_height * 0.75 + chord_size)

    # Render columns top-down, left-to-right
    start_y = y
    current_size = header_size  # Track current font size to avoid redundant blf.size() calls
    
    for col_idx, col_rows in enumerate(columns):
        cx = x + col_idx * (col_w + col_gap)
        cy = start_y

        # Icon, token, label layout
        # Minimal gap between icon and chord
        icon_x = cx
        icon_gap = -16  # Minimal gap between icon and chord
        token_col_right_x = cx + icon_size + icon_gap + max_token_w
        label_col_x = token_col_right_x + gap

        for r in col_rows:
            if r["kind"] == "header":
                if current_size != body_size:
                    blf.size(0, body_size)
                    current_size = body_size
                blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
                blf.position(0, icon_x, cy, 0)
                blf.draw(0, r["text"])
                cy -= line_h
                continue

            # item row
            token_txt = r["token"]
            label_txt = r["label"]
            icon_text = r.get("icon", "")

            # Draw icon if present
            if icon_text:
                try:
                    blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                    draw_icon(icon_text, icon_x, cy, icon_size)
                except Exception:
                    pass

            # Draw token (right-aligned)
            if current_size != chord_size:
                blf.size(0, chord_size)
                current_size = chord_size
            blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
            tw, _ = blf.dimensions(0, token_txt)
            blf.position(0, token_col_right_x - tw, cy, 0)
            blf.draw(0, token_txt)

            # Draw label
            if current_size != body_size:
                blf.size(0, body_size)
                current_size = body_size
            blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
            blf.position(0, label_col_x, cy, 0)
            blf.draw(0, label_txt)
            cy -= line_h

    # Render footer at the bottom
    if footer:
        # Add spacing before footer
        footer_y = start_y - (len(columns[0]) * line_h if columns and columns[0] else 0) - chord_size

        # Calculate total footer width
        icon_gap = 2  # Minimal gap between icon and chord
        footer_item_width = icon_size + icon_gap + max_token_w + gap + max_label_w
        total_footer_width = len(footer) * footer_item_width + (len(footer) - 1) * gap
        
        # Center the footer relative to full viewport width
        footer_x = (region_w - total_footer_width) // 2
        
        # Draw dark background for footer (full width, vertically centered)
        # Calculate text center and height
        text_center_y = footer_y + (chord_size / 2)
        text_height = max(chord_size, body_size) * 1.3
        
        # Full width background
        bg_x1 = 0
        bg_x2 = region_w
        
        # Vertically centered around text
        bg_y1 = text_center_y - (text_height * 0.75)
        bg_y2 = text_center_y + (text_height * 0.45)
        
        # Enable GPU blending for transparency
        gpu.state.blend_set('ALPHA')
        
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        vertices = (
            (bg_x1, bg_y1),
            (bg_x2, bg_y1),
            (bg_x2, bg_y2),
            (bg_x1, bg_y2),
        )
        indices = ((0, 1, 2), (0, 2, 3))
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        shader.bind()
        shader.uniform_float("color", (0.0, 0.0, 0.0, 0.35))
        batch.draw(shader)
        
        # Restore default blending
        gpu.state.blend_set('NONE')

        icon_x = footer_x
        icon_gap = 2  # Minimal gap between icon and chord
        token_col_right_x = footer_x + icon_size + icon_gap + max_token_w
        label_col_x = token_col_right_x + gap
        
        # Set chord_size once for all footer tokens
        blf.size(0, chord_size)

        for r in footer:
            token_txt = r["token"]
            label_txt = r["label"]
            icon_text = r.get("icon", "")

            # Draw icon if present
            if icon_text:
                try:
                    blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                    draw_icon(icon_text, icon_x, footer_y, icon_size)
                except Exception:
                    pass

            # Draw token in angle brackets
            blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
            display_token = f"<{token_txt.lower()}>"
            tw, _ = blf.dimensions(0, display_token)
            blf.position(0, token_col_right_x - tw, footer_y, 0)
            blf.draw(0, display_token)

            # Draw label
            blf.size(0, body_size)
            blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
            blf.position(0, label_col_x, footer_y, 0)
            blf.draw(0, label_txt)
            
            # Reset to chord size for next token
            blf.size(0, chord_size)

            # Move to next footer item
            footer_x += footer_item_width + gap
            icon_x = footer_x
            token_col_right_x = footer_x + icon_size + gap // 2 + max_token_w
            label_col_x = token_col_right_x + gap


def draw_overlay(context, p, buffer_tokens):
    """Main draw callback for the overlay."""
    try:
        import blf  # type: ignore
    except Exception:
        return

    # Basic metrics
    region_w = context.region.width if context.region else 600
    region_h = context.region.height if context.region else 400

    # Check cache validity
    buffer_key = tuple(buffer_tokens) if buffer_tokens else ()
    prefs_hash = get_prefs_hash(p, region_w, region_h)
    
    cache_valid = (
        _overlay_cache["buffer_tokens"] == buffer_key and
        _overlay_cache["prefs_hash"] == prefs_hash and
        _overlay_cache["layout_data"] is not None
    )

    if cache_valid:
        # Use cached layout data
        layout = _overlay_cache["layout_data"]
    else:
        # Recalculate layout
        scale_factor = calculate_scale_factor(context)
        pad_x = int(p.overlay_offset_x * scale_factor)
        pad_y = int(p.overlay_offset_y * scale_factor)

        # Compute candidates
        cands = candidates_for_prefix(p.mappings, buffer_tokens)
        cands.sort(key=lambda c: (c.group.lower(), c.next_token))
        cands = cands[: p.overlay_max_items]

        # Display buffer with + separator instead of spaces
        prefix = "+".join(buffer_tokens) if buffer_tokens else "> ..."
        header = f"Chord Song  |  {prefix}"

        # Scale font sizes
        header_size = max(int(p.overlay_font_size_header * scale_factor), 12)
        chord_size = max(int(p.overlay_font_size_chord * scale_factor), 11)
        body_size = max(int(p.overlay_font_size_body * scale_factor), 10)
        icon_size = chord_size

        # Precompute layout dimensions
        blf.size(0, header_size)
        header_w, header_h = blf.dimensions(0, header)

        # Scale spacing
        gap = int(10 * scale_factor)
        col_gap = int(30 * scale_factor)
        line_h = int(body_size * 1.5)

        # Build rows and footer
        rows, footer = build_overlay_rows(cands, bool(buffer_tokens))
        max_rows = max(int(p.overlay_column_rows), 1)
        columns = wrap_into_columns(rows, max_rows)

        # Calculate dimensions (including icon space and footer)
        max_token_w, max_label_w, max_header_row_w = calculate_column_widths(columns, footer, chord_size, body_size)

        # Account for icon in column width (using smaller icon_gap)
        icon_gap = 2  # Minimal gap between icon and chord
        col_w = max(icon_size + icon_gap + max_token_w + gap + max_label_w, max_header_row_w)

        num_cols = len(columns)
        block_w = max(header_w, num_cols * col_w + (num_cols - 1) * col_gap)
        max_rows_in_any = min(max_rows, max(len(c) for c in columns) if columns else 0)

        # Add extra space for footer
        footer_rows = 1 if footer else 0
        block_h = int(header_h + (line_h * (max_rows_in_any + footer_rows + 2)))

        # Calculate position
        x, y = calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y)

        # Store layout in cache
        layout = {
            "columns": columns,
            "footer": footer,
            "x": x,
            "y": y,
            "header": header,
            "header_size": header_size,
            "header_w": header_w,
            "chord_size": chord_size,
            "body_size": body_size,
            "max_token_w": max_token_w,
            "gap": gap,
            "col_w": col_w,
            "col_gap": col_gap,
            "line_h": line_h,
            "icon_size": icon_size,
            "block_w": block_w,
            "max_label_w": max_label_w,
        }

        _overlay_cache["buffer_tokens"] = buffer_key
        _overlay_cache["prefs_hash"] = prefs_hash
        _overlay_cache["layout_data"] = layout

    # Render (always done, only layout calculation is cached)
    render_overlay(
        context, p,
        layout["columns"],
        layout["footer"],
        layout["x"],
        layout["y"],
        layout["header"],
        layout["header_size"],
        layout["chord_size"],
        layout["body_size"],
        layout["max_token_w"],
        layout["gap"],
        layout["col_w"],
        layout["col_gap"],
        layout["line_h"],
        layout["icon_size"],
        layout["block_w"],
        layout["max_label_w"],
        region_w,
        layout["header_w"],
    )


def draw_fading_overlay(context, p, chord_text, label, icon, start_time, fade_duration=1.5):
    """Draw a fading overlay showing the executed chord."""
    try:
        import blf  # type: ignore
    except Exception:
        return False

    # Calculate fade alpha based on elapsed time
    elapsed = time.time() - start_time
    if elapsed >= fade_duration:
        return False  # Signal that overlay should be removed

    # Fade out: alpha goes from 1.0 to 0.0
    fade_alpha = max(0.0, 1.0 - (elapsed / fade_duration))

    # Basic metrics
    region_w = context.region.width if context.region else 600
    region_h = context.region.height if context.region else 400

    scale_factor = calculate_scale_factor(context)
    
    # Font sizes
    header_size = max(int(p.overlay_font_size_header * scale_factor), 12)
    body_size = max(int(p.overlay_font_size_body * scale_factor), 10)
    icon_size = header_size

    # Measure text dimensions
    blf.size(0, header_size)
    chord_w, _ = blf.dimensions(0, chord_text)
    
    blf.size(0, body_size)
    label_w, _ = blf.dimensions(0, label)

    # Layout
    gap = int(10 * scale_factor)
    pad_x = int(p.overlay_offset_x * scale_factor)
    pad_y = int(p.overlay_offset_y * scale_factor)
    
    # Calculate content width (smaller gap between icon and chord)
    icon_w = icon_size if icon else 0
    icon_gap = 2 if icon else 0  # Minimal gap between icon and chord
    content_w = icon_w + chord_w + gap + label_w

    # Position at the same level as the main overlay header
    # Calculate position using same logic as main overlay
    block_h = int(header_size * 1.8)  # Approximate height for positioning
    _, y = calculate_overlay_position(p, region_w, region_h, content_w, block_h, pad_x, pad_y)
    
    # Calculate text center and height for vertical centering
    text_center_y = y + (header_size / 2)
    text_height = max(header_size, body_size) * 1.3
    
    # Full width background
    bg_x1 = 0
    bg_x2 = region_w
    
    # Vertically centered around text
    bg_y1 = text_center_y - (text_height * 0.75)
    bg_y2 = text_center_y + (text_height * 0.45)

    # Draw semi-transparent background with fade (full width)
    bg_alpha = 0.35 * fade_alpha
    
    gpu.state.blend_set('ALPHA')
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    vertices = (
        (bg_x1, bg_y1),
        (bg_x2, bg_y1),
        (bg_x2, bg_y2),
        (bg_x1, bg_y2),
    )
    indices = ((0, 1, 2), (0, 2, 3))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", (0.0, 0.0, 0.0, bg_alpha))
    batch.draw(shader)
    gpu.state.blend_set('NONE')

    # Draw content (centered horizontally)
    text_y = y
    current_x = (region_w - content_w) // 2

    # Draw icon if present
    if icon:
        try:
            col_icon = p.overlay_color_icon
            blf.size(0, icon_size)
            blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3] * fade_alpha)
            blf.position(0, current_x, text_y, 0)
            blf.draw(0, icon)
        except Exception:
            pass
        current_x += icon_w + icon_gap

    # Draw chord text
    col_chord = p.overlay_color_chord
    blf.size(0, header_size)
    blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3] * fade_alpha)
    blf.position(0, current_x, text_y, 0)
    blf.draw(0, chord_text)
    current_x += chord_w + gap

    # Draw label
    col_label = p.overlay_color_label
    blf.size(0, body_size)
    label_y = text_y + (header_size - body_size) // 3  # Vertically align with chord
    blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * fade_alpha)
    blf.position(0, current_x, label_y, 0)
    blf.draw(0, label)

    return True  # Continue showing overlay
