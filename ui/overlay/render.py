"""Rendering functions for the overlay."""
import time
import gpu  # type: ignore
from gpu_extras.batch import batch_for_shader  # type: ignore
from ...utils.render import calculate_scale_factor, calculate_overlay_position
from ...core.engine import candidates_for_prefix, get_leader_key_token
from .cache import _overlay_cache, get_prefs_hash
from .layout import build_overlay_rows, wrap_into_columns, calculate_column_widths

def draw_icon(icon_text, x, y, size):
    """Draw a Nerd Fonts icon/emoji at the specified position."""
    if not icon_text:
        return

    import blf  # type: ignore

    # Draw the icon as text using the current font
    blf.size(0, size)
    blf.position(0, x, y, 0)
    blf.draw(0, icon_text)

def draw_rect(x1, y1, x2, y2, color):
    """Draw a filled rectangle with the given color."""
    if color[3] < 0.001:  # Only draw if visible
        return

    gpu.state.blend_set('ALPHA')
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    vertices = (
        (x1, y1),
        (x2, y1),
        (x2, y2),
        (x1, y2),
    )
    indices = ((0, 1, 2), (0, 2, 3))
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set('NONE')

def draw_overlay_header(p, region_w, y, header_text, header_size, body_size, chord_size, header_w):
    """Draw the overlay header background and text."""
    import blf # type: ignore

    # Calculate metrics
    text_center_y = y + (header_size / 2)
    text_height = max(header_size, body_size) * 1.3

    # Vertically centered around text
    bg_y1 = text_center_y - (text_height * 0.75)
    bg_y2 = text_center_y + (text_height * 0.45)

    # Draw background
    draw_rect(0, bg_y1, region_w, bg_y2, p.overlay_header_background)

    # Draw text
    col_header = p.overlay_color_header
    header_x = (region_w - header_w) // 2
    blf.size(0, header_size)
    blf.color(0, col_header[0], col_header[1], col_header[2], col_header[3])
    blf.position(0, header_x, y, 0)
    blf.draw(0, header_text)

    # Return new Y position for content and bg_y1 for list background connection
    new_y = y - int(header_size / 2 + text_height * 0.75 + chord_size)
    return new_y, bg_y1

def draw_list_background(p, region_w, top_y, bottom_y):
    """Draw the background for the list area."""
    draw_rect(0, bottom_y, region_w, top_y, p.overlay_list_background)

def draw_overlay_footer(p, region_w, footer_y, footer_items, chord_size, body_size, scale_factor, icon_size, max_token_w, max_label_w):
    """Draw the overlay footer background and items."""
    import blf # type: ignore

    col_chord = p.overlay_color_chord
    col_label = p.overlay_color_label
    col_icon = p.overlay_color_icon

    # Calculate metrics
    text_center_y = footer_y + (chord_size / 2)
    text_height = max(chord_size, body_size) * 1.3

    bg_y1 = text_center_y - (text_height * 0.75)
    bg_y2 = text_center_y + (text_height * 0.45)

    # Draw background
    draw_rect(0, bg_y1, region_w, bg_y2, p.overlay_footer_background)

    # Calculate layout
    footer_token_gap = int(p.overlay_footer_token_gap * scale_factor)
    footer_label_gap = int(p.overlay_footer_label_gap * scale_factor)
    footer_item_width = max_token_w + footer_token_gap + icon_size + footer_label_gap + max_label_w
    footer_gap = int(p.overlay_footer_gap * scale_factor)
    total_footer_width = len(footer_items) * footer_item_width + (len(footer_items) - 1) * footer_gap

    footer_x = (region_w - total_footer_width) // 2

    blf.size(0, chord_size)

    for r in footer_items:
        token_txt = r["token"]
        label_txt = r["label"]
        icon_text = r.get("icon", "")

        # Update token for "Recent Commands"
        if label_txt == "Recent Commands" and "+" in token_txt:
            leader_token = get_leader_key_token()
            token_txt = f"{leader_token}+{leader_token}"

        token_x = footer_x

        # Draw token
        blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
        display_token = f"<{token_txt.upper()}>"
        tw, _ = blf.dimensions(0, display_token)
        blf.position(0, token_x, footer_y, 0)
        blf.draw(0, display_token)

        # Draw icon
        icon_x = token_x + tw + footer_token_gap
        if icon_text:
            try:
                blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                draw_icon(icon_text, icon_x, footer_y, icon_size)
            except Exception:
                pass

        # Draw label
        label_x = icon_x + (icon_size if icon_text else 0) + (footer_label_gap if icon_text else footer_token_gap)
        blf.size(0, body_size)
        blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
        blf.position(0, label_x, footer_y, 0)
        blf.draw(0, label_txt)

        blf.size(0, chord_size)
        footer_x += footer_item_width + footer_gap

    return bg_y2 # Return top of footer bg (for list bg connection)

def render_overlay(_context, p, columns, footer, x, y, header, header_size, chord_size, body_size,
                   column_metrics, footer_metrics, gap, col_gap, line_h, icon_size, block_w, block_h, region_w, header_w, header_h):
    """Render the overlay at the calculated position."""
    import blf  # type: ignore

    scale_factor = calculate_scale_factor(_context)
    col_chord = p.overlay_color_chord
    col_label = p.overlay_color_label
    col_icon = p.overlay_color_icon
    col_header = p.overlay_color_header

    # 1. Draw Header
    if p.overlay_show_header:
        current_y, header_bg_bottom = draw_overlay_header(p, region_w, y, header, header_size, body_size, chord_size, header_w)
    else:
        current_y = y
        # Adjust top of background to cover the first line's text ascender
        header_bg_bottom = y + line_h

    # 2. Calculate Footer Position & List Bg Bottom
    start_y = current_y

    num_rows = max(len(c) for c in columns) if columns else 0
    list_content_height = num_rows * line_h

    if footer and p.overlay_show_footer:
        footer_y = start_y - (len(columns[0]) * line_h if columns and columns[0] else 0) - chord_size

        # Calculate scale factor for footer text size
        footer_text_size_base = getattr(p, "overlay_font_size_footer", 12)
        footer_text_size = max(int(footer_text_size_base * scale_factor), 10)

        # Draw footer and get its top bg (which is list bottom)
        # Use footer_metrics for alignment
        footer_bg_top = draw_overlay_footer(p, region_w, footer_y, footer, footer_text_size, footer_text_size,
                                            scale_factor, icon_size, footer_metrics["token"], footer_metrics["label"])
    else:
        # Move bottom up by roughly one line height + some padding adjustment
        footer_bg_top = start_y - list_content_height + line_h * 0.5

    # 3. Draw List Background
    draw_list_background(p, region_w, header_bg_bottom, footer_bg_top)

    # 4. Draw Columns
    current_size = chord_size # Init

    current_x_offset = 0

    for col_idx, col_rows in enumerate(columns):
        if col_idx >= len(column_metrics):
             break

        metrics = column_metrics[col_idx]
        col_total_w = metrics["total_w"]

        cx = x + current_x_offset
        cy = start_y

        icon_x = cx
        token_col_left_x = cx + icon_size + gap
        # Labels are now positioned dynamically per row to keep gap constant

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

            # Draw icon
            if icon_text:
                try:
                    blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                    draw_icon(icon_text, icon_x, cy, icon_size)
                except Exception:
                    pass

            # Draw token
            if current_size != chord_size:
                blf.size(0, chord_size)
                current_size = chord_size
            blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
            blf.position(0, token_col_left_x, cy, 0)
            blf.draw(0, token_txt)

            # Calculate token width for dynamic label positioning
            tw, _ = blf.dimensions(0, token_txt)
            label_x = token_col_left_x + tw + gap

            # Draw label
            if current_size != body_size:
                blf.size(0, body_size)
                current_size = body_size
            blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
            blf.position(0, label_x, cy, 0)
            blf.draw(0, label_txt)
            cy -= line_h

        current_x_offset += col_total_w + col_gap

def draw_overlay(context, p, buffer_tokens, filtered_mappings=None):
    """Main draw callback for the overlay.

    Args:
        context: Blender context
        p: Addon preferences
        buffer_tokens: Current buffer of chord tokens
        filtered_mappings: Optional filtered mappings list (defaults to p.mappings)
    """
    try:
        import blf  # type: ignore
    except Exception:
        return

    # Use filtered mappings if provided, otherwise use all mappings
    if filtered_mappings is None:
        filtered_mappings = p.mappings

    # Basic metrics
    region_w = context.region.width if context.region else 600
    region_h = context.region.height if context.region else 400

    # Generate signature for mappings to prevent cache collision (e.g. between Test and Leader)
    mappings_sig = (len(filtered_mappings), getattr(filtered_mappings[0], 'chord', '') if filtered_mappings else None)

    # Check cache validity
    buffer_key = tuple(buffer_tokens) if buffer_tokens else ()
    prefs_hash = get_prefs_hash(p, region_w, region_h)

    cache_valid = (
        _overlay_cache["buffer_tokens"] == buffer_key and
        _overlay_cache["prefs_hash"] == prefs_hash and
        _overlay_cache.get("mappings_sig") == mappings_sig and
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

        # Compute candidates from filtered mappings
        cands = candidates_for_prefix(filtered_mappings, buffer_tokens)
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

        # Scale spacing (using preferences)
        gap = int(p.overlay_gap * scale_factor)
        col_gap = int(p.overlay_column_gap * scale_factor)
        line_h = int(body_size * p.overlay_line_height)

        # Build rows and footer
        rows, footer = build_overlay_rows(cands, bool(buffer_tokens))
        max_rows = max(int(p.overlay_column_rows), 1)
        columns = wrap_into_columns(rows, max_rows)

        # Calculate dimensions
        col_metrics, footer_metrics = calculate_column_widths(columns, footer, chord_size, body_size)

        # Calculate width per column
        total_cols_w = 0
        for m in col_metrics:
            content_w = icon_size + gap + m["token"] + gap + m["label"]
            width = max(content_w, m["header"])
            m["total_w"] = width
            total_cols_w += width

        num_cols = len(col_metrics)

        # Calculate block width
        effective_header_w = header_w if p.overlay_show_header else 0
        cols_gap_total = (num_cols - 1) * col_gap if num_cols > 1 else 0
        block_w = max(effective_header_w, total_cols_w + cols_gap_total)

        max_rows_in_any = min(max_rows, max(len(c) for c in columns) if columns else 0)

        # Add extra space for footer
        footer_rows = 1 if (footer and p.overlay_show_footer) else 0

        # Calculate block height
        if p.overlay_show_header:
            block_h = int(header_h + (line_h * (max_rows_in_any + footer_rows + 2)))
        else:
            block_h = int(line_h * (max_rows_in_any + footer_rows + 1.5))

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
            "column_metrics": col_metrics,
            "footer_metrics": footer_metrics,
            "gap": gap,
            "col_gap": col_gap,
            "line_h": line_h,
            "icon_size": icon_size,
            "block_w": block_w,
            "block_h": block_h,
            "header_h": header_h,
        }

        _overlay_cache["buffer_tokens"] = buffer_key
        _overlay_cache["prefs_hash"] = prefs_hash
        _overlay_cache["mappings_sig"] = mappings_sig
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
        layout["column_metrics"],
        layout["footer_metrics"],
        layout["gap"],
        layout["col_gap"],
        layout["line_h"],
        layout["icon_size"],
        layout["block_w"],
        layout["block_h"],
        region_w,
        layout["header_w"],
        layout["header_h"],
    )

def draw_fading_overlay(context, p, chord_text, label, icon, start_time, fade_duration=1.5):
    """Draw a fading overlay showing the executed chord."""
    # Check if fading overlay is enabled
    if not getattr(p, "overlay_fading_enabled", True):
        return False

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

    # Font sizes - Use fading specific size for main text
    fading_size_base = getattr(p, "overlay_font_size_fading", 24)
    header_size = max(int(fading_size_base * scale_factor), 12)

    # Scale label (body) proportionally to fading size (e.g. 70%)
    body_size = max(int(header_size * 0.7), 10)
    icon_size = header_size

    # Measure text dimensions
    blf.size(0, header_size)
    chord_w, _ = blf.dimensions(0, chord_text)

    blf.size(0, body_size)
    label_w, _ = blf.dimensions(0, label)

    # Layout (using preferences)
    gap = int(p.overlay_gap * scale_factor)
    pad_x = int(p.overlay_offset_x * scale_factor)
    pad_y = int(p.overlay_offset_y * scale_factor)

    # Calculate content width
    icon_w = icon_size if icon else 0
    content_w = icon_w + gap + chord_w + gap + label_w

    # Position at the same level as the main overlay header
    # Calculate position using same logic as main overlay
    block_h = int(header_size * 1.8)  # Approximate height for positioning
    _, y = calculate_overlay_position(p, region_w, region_h, content_w, block_h, pad_x, pad_y)

    # User requested position "between footer and header", i.e., in the body area.
    # For Top alignment, this means pushing it down below the header area.
    # For Bottom alignment, the calculate_position with a small height naturally puts it at the bottom (body area),
    # so we don't need to offset (and doing so would push it off screen).
    is_top_aligned = "TOP" in p.overlay_position or "CENTER_TOP" in p.overlay_position

    if getattr(p, "overlay_show_header", True) and is_top_aligned:
         # Roughly header metrics from draw_overlay_header: text_height * 0.75 + padding
         header_clearance = int(max(header_size, body_size) * 1.8)
         y -= header_clearance

    # Calculate text center and height for vertical centering
    # Revert to original relative calculation so background matches text baseline (y)
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
        current_x += icon_w + gap

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
    # Remove label_y offset to keep baselines aligned
    blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * fade_alpha)
    blf.position(0, current_x, text_y, 0)
    blf.draw(0, label)

    return True  # Continue showing overlay
