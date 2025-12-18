"""Cache state and management for overlay."""

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
        p.overlay_list_background,
        p.overlay_header_background,
        p.overlay_footer_background,
        region_w,
        region_h,
    )
