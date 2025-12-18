"""Layout calculation functions for overlay."""
from ...core.engine import get_leader_key_token


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
