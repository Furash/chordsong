"""Overlay rendering for chord capture display."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import time
import bpy  # type: ignore
from ..core.engine import candidates_for_prefix, normalize_token

# Import gpu modules at module level for better performance
import gpu  # type: ignore
from gpu_extras.batch import batch_for_shader  # type: ignore


def get_leader_key_token():
    """Get the current leader key token for display."""
    try:
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            return "<Leader>"
        
        km = kc.keymaps.get("3D View")
        if not km:
            return "<Leader>"
        
        # Find the leader keymap item
        for kmi in km.keymap_items:
            if kmi.idname == "chordsong.leader":
                # Normalize the key type to a display token
                # Check if shift is required for this keymap item
                shift_state = getattr(kmi, "shift", False)
                token = normalize_token(kmi.type, shift=shift_state)
                if token:
                    return token
                # Fallback: if normalization fails, try to use the key type directly
                # (for debugging or unrecognized keys)
                if kmi.type:
                    return kmi.type.lower()
                return "<Leader>"
        
        return "<Leader>"
    except Exception:
        return "<Leader>"


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
        p.overlay_gap,
        p.overlay_column_gap,
        p.overlay_line_height,
        p.overlay_footer_gap,
        p.overlay_footer_token_gap,
        p.overlay_footer_label_gap,
        region_w,
        region_h,
    )


def build_overlay_rows(cands, has_buffer, mappings=None):
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
            
            rows.append({"kind": "item", "token": token, "label": label, "icon": icon})
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
            
            rows.append({"kind": "item", "token": token, "label": label, "icon": icon})
        else:
            # Single final chord, show its label
            c = group[0]
            rows.append({"kind": "item", "token": c.next_token or "", "label": c.label, "icon": c.icon})

    # Footer items (always at bottom)
    footer = []
    if not has_buffer:
        # Only show recents at root level (no buffer)
        leader_token = get_leader_key_token()
        footer.append({"kind": "item", "token": f"{leader_token}+{leader_token}", "label": "Recent Commands", "icon": ""})
    
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
    
    # Calculate scale factor for footer gap
    scale_factor = calculate_scale_factor(_context)

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
        # Use consistent gap between all elements
        icon_x = cx
        token_col_left_x = cx + icon_size + gap
        label_col_x = token_col_left_x + gap * 2

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

            # Draw token (left-aligned after icon)
            if current_size != chord_size:
                blf.size(0, chord_size)
                current_size = chord_size
            blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
            blf.position(0, token_col_left_x, cy, 0)
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

        # Calculate total footer width (token, then icon, then label)
        footer_token_gap = int(p.overlay_footer_token_gap * scale_factor)  # Gap between token and icon/label
        footer_label_gap = int(p.overlay_footer_label_gap * scale_factor)  # Gap between icon and label
        footer_item_width = max_token_w + footer_token_gap + icon_size + footer_label_gap + max_label_w
        footer_gap = int(p.overlay_footer_gap * scale_factor)  # Gap between footer items
        total_footer_width = len(footer) * footer_item_width + (len(footer) - 1) * footer_gap
        
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
        
        # Set chord_size once for all footer tokens
        blf.size(0, chord_size)

        for r in footer:
            token_txt = r["token"]
            label_txt = r["label"]
            icon_text = r.get("icon", "")

            # Update token for "Recent Commands" to use current leader key
            if label_txt == "Recent Commands" and "+" in token_txt:
                leader_token = get_leader_key_token()
                token_txt = f"{leader_token}+{leader_token}"

            # Calculate positions for this item: token, then icon, then label
            token_x = footer_x
            
            # Draw token in angle brackets first (uppercase to match footer style)
            blf.color(0, col_chord[0], col_chord[1], col_chord[2], col_chord[3])
            display_token = f"<{token_txt.upper()}>"
            tw, _ = blf.dimensions(0, display_token)
            blf.position(0, token_x, footer_y, 0)
            blf.draw(0, display_token)
            
            # Icon comes after token
            icon_x = token_x + tw + footer_token_gap
            if icon_text:
                try:
                    blf.color(0, col_icon[0], col_icon[1], col_icon[2], col_icon[3])
                    draw_icon(icon_text, icon_x, footer_y, icon_size)
                except Exception:
                    pass
            
            # Label comes after icon (or token if no icon)
            label_x = icon_x + (icon_size if icon_text else 0) + (footer_label_gap if icon_text else footer_token_gap)
            blf.size(0, body_size)
            blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3])
            blf.position(0, label_x, footer_y, 0)
            blf.draw(0, label_txt)
            
            # Reset to chord size for next token
            blf.size(0, chord_size)

            # Move to next footer item
            footer_x += footer_item_width + footer_gap


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

        # Calculate dimensions (including icon space and footer)
        max_token_w, max_label_w, max_header_row_w = calculate_column_widths(columns, footer, chord_size, body_size)

        # Account for icon in column width (using consistent gap)
        col_w = max(icon_size + gap + max_token_w + gap + max_label_w, max_header_row_w)

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
    label_y = text_y + (header_size - body_size) // 3  # Vertically align with chord
    blf.color(0, col_label[0], col_label[1], col_label[2], col_label[3] * fade_alpha)
    blf.position(0, current_x, label_y, 0)
    blf.draw(0, label)

    return True  # Continue showing overlay
