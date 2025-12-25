"""Layout calculation functions for overlay."""
from ...core.engine import get_leader_key_token

def build_overlay_rows(cands, has_buffer, mappings=None):
    """Build display rows from candidates, footer returned separately."""
    rows = []
    
    # Sort candidates by group then token
    sorted_cands = sorted(cands, key=lambda c: (c.group.lower(), c.next_token))
    
    for c in sorted_cands:
        token = c.next_token
        icon = c.icon if c.icon else ""
        
        if c.count > 1 or not c.is_final:
            # Folder/Summary row - always use folder style if not a final command
            # No icon for summary/folder items
            suffix = "s" if c.count > 1 else ""
            label = f"→  +{c.count} keymap{suffix}"
            rows.append({"kind": "item", "token": token, "label": label, "icon": ""})
        else:
            # Single final chord, show its label
            rows.append({"kind": "item", "token": token, "label": c.label, "icon": icon})

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
    """Calculate token and label widths per column and for footer."""
    import blf  # type: ignore

    column_metrics = []

    # Set font sizes once
    blf.size(0, chord_size)

    # Check all columns
    for col in columns:
        col_max_token_w = 0.0
        col_max_label_w = 0.0
        col_max_header_w = 0.0
        has_any_icon = False

        for r in col:
            if r["kind"] == "header":
                blf.size(0, body_size)
                w, _ = blf.dimensions(0, r["text"])
                col_max_header_w = max(col_max_header_w, w)
                blf.size(0, chord_size)
            else:
                if r.get("icon"):
                    has_any_icon = True
                
                # Token width
                tw, _ = blf.dimensions(0, f"{r['token'].upper()}")
                col_max_token_w = max(col_max_token_w, tw)

                # Label width
                blf.size(0, body_size)
                lw, _ = blf.dimensions(0, r["label"])
                col_max_label_w = max(col_max_label_w, lw)
                blf.size(0, chord_size)

        column_metrics.append({
            "token": col_max_token_w,
            "label": col_max_label_w,
            "header": col_max_header_w,
            "has_icons": has_any_icon
        })

    # Check footer items
    f_token_w = 0.0
    f_label_w = 0.0
    for r in footer:
        tw, _ = blf.dimensions(0, f"{r['token'].upper()}")
        f_token_w = max(f_token_w, tw)

        blf.size(0, body_size)
        lw, _ = blf.dimensions(0, r["label"])
        f_label_w = max(f_label_w, lw)
        blf.size(0, chord_size)

    return column_metrics, {"token": f_token_w, "label": f_label_w}
