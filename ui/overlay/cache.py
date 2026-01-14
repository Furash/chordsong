"""Cache state and management for overlay."""

# Cache for overlay layout to avoid recalculating every frame
_overlay_cache = {
    "buffer_tokens": None,
    "prefs_hash": None,
    "layout_data": None,
    "filepath": None,
}

def clear_overlay_cache():
    """Clear the overlay cache. Call when mappings are updated."""
    _overlay_cache["buffer_tokens"] = None
    _overlay_cache["prefs_hash"] = None
    _overlay_cache["layout_data"] = None
    _overlay_cache["filepath"] = None

def get_prefs_hash(p, region_w, region_h):
    """Get a hash of preferences that affect overlay layout."""
    return (
        p.overlay_font_size_header,
        p.overlay_font_size_chord,
        p.overlay_font_size_body,
        p.overlay_font_size_toggle,  # Toggle icon size
        p.overlay_column_rows,
        p.overlay_max_items,
        p.overlay_max_label_length,  # Include label truncation setting
        p.overlay_offset_x,
        p.overlay_offset_y,
        p.overlay_position,
        p.overlay_gap,
        p.overlay_column_gap,
        p.overlay_line_height,
        p.overlay_footer_gap,
        p.overlay_footer_token_gap,
        p.overlay_footer_label_gap,
        p.overlay_folder_style,
        # Format string settings (for CUSTOM style)
        getattr(p, "overlay_format_item", "C I L"),
        getattr(p, "overlay_format_folder", "C G S N"),
        getattr(p, "overlay_separator_a", "→"),
        getattr(p, "overlay_separator_b", "::"),
        p.overlay_list_background,
        p.overlay_header_background,
        p.overlay_footer_background,
        region_w,
        region_h,
    )
