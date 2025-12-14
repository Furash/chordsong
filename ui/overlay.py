"""Overlay rendering for chord capture display."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

from ..core.engine import candidates_for_prefix


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
        # If multiple chords share this prefix, show a summary
        if len(group) > 1:
            # Use first icon if available, or empty string
            icon = group[0].icon if group[0].icon else ""
            
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
            # Single chord, show its label
            c = group[0]
            rows.append({"kind": "item", "token": (c.next_token or "").upper(), "label": c.label, "icon": c.icon})

    # Footer items (always at bottom)
    footer = []
    footer.append({"kind": "item", "token": "ESC", "label": "Close", "icon": "󰅖"})
    if has_buffer:
        footer.append({"kind": "item", "token": "BS", "label": "Back"})

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


def calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y):
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
                   max_token_w, gap, col_w, col_gap, line_h, icon_size):
    """Render the overlay at the calculated position."""
    import blf  # type: ignore

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

        # Icon, token, label layout
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
            icon_text = r.get("icon", "")

            # Draw icon if present
            if icon_text:
                try:
                    # Set icon color (same as labels but slightly dimmed)
                    blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * 0.7)
                    draw_icon(icon_text, icon_x, cy, icon_size)
                except Exception:
                    pass

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
            icon_text = r.get("icon", "")

            # Draw icon if present
            if icon_text:
                try:
                    blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * 0.7)
                    draw_icon(icon_text, icon_x, footer_y, icon_size)
                except Exception:
                    pass

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


def draw_overlay(context, p, buffer_tokens):
    """Main draw callback for the overlay."""
    try:
        import blf  # type: ignore
    except Exception:
        return

    # Basic metrics
    region_w = context.region.width if context.region else 600
    region_h = context.region.height if context.region else 400

    scale_factor = calculate_scale_factor(context)
    pad_x = int(getattr(p, "overlay_offset_x", 14) * scale_factor)
    pad_y = int(getattr(p, "overlay_offset_y", 14) * scale_factor)

    # Compute candidates
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
    rows, footer = build_overlay_rows(cands, bool(buffer_tokens))
    max_rows = max(int(getattr(p, "overlay_column_rows", 12)), 3)
    columns = wrap_into_columns(rows, max_rows)

    # Calculate dimensions (including icon space and footer)
    max_token_w, max_label_w, max_header_row_w = calculate_column_widths(columns, footer, chord_size, body_size)

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
    x, y = calculate_overlay_position(p, region_w, region_h, block_w, block_h, pad_x, pad_y)

    # Render
    render_overlay(context, p, columns, footer, x, y, header, header_size, chord_size, body_size,
                   max_token_w, gap, col_w, col_gap, line_h, icon_size)
