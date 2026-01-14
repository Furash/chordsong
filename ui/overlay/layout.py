"""Layout calculation functions for overlay."""
from ...core.engine import get_leader_key_token
from .tokenizer import (
    parse_format_string,
    generate_tokens_for_folder,
    generate_tokens_for_item,
    tokens_to_display_parts,
)

def _get_preset_formats(style):
    """Get format strings for preset styles.
    
    Each preset maps to specific format strings for folders and items:
    - DEFAULT: Simple count display
      Folder: "a → +5 keymaps"
      Item: "a  Save"
    - GROUPS_AFTER: Count first, then groups
      Folder: "a → +5 keymaps :: Modeling"
      Item: "a  Save"
    - GROUPS_FIRST: Groups first, then count
      Folder: "a → Modeling → 5 keymaps"
      Item: "a  Save"
    - HYBRID: Minimal with groups and compact count
      Folder: "a → Modeling :: +5"
      Item: "a  Save"
    - CUSTOM: User-defined format strings
    
    Token types:
    - C: Chord, I: Icon, G: Groups (all), g: Group (first only)
    - L: Label, N: Count (verbose), n: Count (compact)
    - S: Separator A (→), s: Separator B (::)
    - T: Toggle icon
    
    Returns: (folder_format, item_format, separator_a, separator_b)
    """
    presets = {
        "DEFAULT": ("C S N", "C I L T", "→", "::"),
        "GROUPS_AFTER": ("C S N s G", "C I L T", "→", "::"),
        "GROUPS_FIRST": ("C S G S N", "C I L T", "→", "::"),
        "HYBRID": ("C S G s n", "C I L T", "→", "::"),
        "CUSTOM": None,  # Use user-defined formats
    }
    return presets.get(style, presets["GROUPS_FIRST"])

def build_overlay_rows(cands, has_buffer, p=None):
    """Build display rows from candidates, footer returned separately."""
    rows = []
    
    # Get style from prefs if available
    style = getattr(p, "overlay_folder_style", "GROUPS_FIRST") if p else "GROUPS_FIRST"
    
    # Get format strings based on style
    if style == "CUSTOM" and p:
        # Use user-defined format strings
        separator_a = getattr(p, "overlay_separator_a", "→")
        separator_b = getattr(p, "overlay_separator_b", "::")
        format_folder = getattr(p, "overlay_format_folder", "C G S N")
        format_item = getattr(p, "overlay_format_item", "C I L T")
    else:
        # Use preset format strings
        preset = _get_preset_formats(style)
        if preset:
            format_folder, format_item, separator_a, separator_b = preset
        else:
            format_folder, format_item, separator_a, separator_b = "C S G S N", "C I L T", "→", "::"
    
    # Sort candidates by group then token
    sorted_cands = sorted(cands, key=lambda c: (c.group.lower(), c.next_token))
    
    for c in sorted_cands:
        token = c.next_token
        icon = c.icon if c.icon else ""
        
        if c.count > 1 or not c.is_final:
            # Folder/Summary row - use tokenization for all styles
            token_types = parse_format_string(format_folder)
            tokens = generate_tokens_for_folder(
                token_types=token_types,
                chord=token,
                icon=icon,
                groups=c.groups if c.groups else [],
                count=c.count,
                separator_a=separator_a,
                separator_b=separator_b,
            )
            
            # Store tokens in the row for rendering
            rows.append({
                "kind": "item",
                "token": token,
                "label": "",
                "label_extra": "",
                "icon": "",
                "tokens": tokens,  # Custom tokens for rendering
            })
        else:
            # Single final chord, show its label
            label = c.label
            icon = c.icon
            label_extra = ""

            # Check for merged extra info (like property values set in engine.py)
            if "::" in label:
                parts = label.split("::", 1)
                label = parts[0].strip()
                label_extra = f":: {parts[1].strip()}"

            # Use tokenization for all styles
            token_types = parse_format_string(format_item)
            tokens = generate_tokens_for_item(
                token_types=token_types,
                chord=token,
                icon=icon,
                groups=c.groups if c.groups else [],
                label=label,
                separator_a=separator_a,
                separator_b=separator_b,
                mapping_type=c.mapping_type,
            )
            
            rows.append({
                "kind": "item",
                "token": token,
                "label": "",
                "label_extra": label_extra if label_extra else "",
                "icon": "",
                "mapping_type": c.mapping_type,
                "tokens": tokens,  # Tokens for rendering
            })

    # Footer items (always at bottom)
    footer = []
    
    # 1. Mod hints (informational)
    footer.append({"kind": "hint", "token": ">R  ^Ctrl  !Alt  +Shift  #Win", "label": "", "icon": ""})

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

def calculate_column_widths(columns, footer, chord_size, body_size, p=None):
    """Calculate token and label widths per column and for footer.
    
    Each format token type becomes its own sub-column with calculated width.
    """
    import blf  # type: ignore

    column_metrics = []
    
    # Get max label length setting for truncation during width calculation
    max_label_length = getattr(p, "overlay_max_label_length", 0) if p else 0
    
    # Get font sizes for different token types
    icon_size = chord_size
    toggle_size = max(int(getattr(p, "overlay_font_size_toggle", 16)), 6) if p else 16

    # Set font sizes once
    blf.size(0, chord_size)

    # Process each column
    for col in columns:
        # Dynamic sub-columns: track max width for each token type
        token_widths = {}  # token_type -> max_width
        
        # Legacy fields
        col_max_header_w = 0.0
        has_any_icon = False

        for r in col:
            if r["kind"] == "header":
                blf.size(0, body_size)
                w, _ = blf.dimensions(0, r["text"])
                col_max_header_w = max(col_max_header_w, w)
                blf.size(0, chord_size)
            else:
                # Check if this row uses custom tokens
                if r.get("tokens"):
                    # Custom format: measure each token with its own font size
                    for tok in r["tokens"]:
                        # Set appropriate font size for this token type
                        if tok.type == 'C':  # Chord
                            blf.size(0, chord_size)
                        elif tok.type == 'I':  # Icon
                            blf.size(0, icon_size)
                            has_any_icon = True
                        elif tok.type in ('T', 't'):  # Toggle
                            blf.size(0, toggle_size)
                        else:  # G, g, L, N, n, S, s - use body size
                            blf.size(0, body_size)
                        
                        # Apply truncation for label tokens
                        content = tok.content
                        if tok.type == 'L' and max_label_length > 0 and len(content) > max_label_length:
                            if max_label_length > 3:
                                content = content[:max_label_length-3] + "..."
                            else:
                                content = content[:max_label_length]
                        
                        # Measure width
                        w, _ = blf.dimensions(0, content)
                        
                        # Track maximum width for this token type
                        token_widths[tok.type] = max(token_widths.get(tok.type, 0.0), w)
                else:
                    # Legacy rendering: use standard 3-column approach
                    # Chord column
                    blf.size(0, chord_size)
                    if r.get("icon"):
                        has_any_icon = True
                        iw, _ = blf.dimensions(0, r["icon"])
                        token_widths['I'] = max(token_widths.get('I', 0.0), iw)
                    
                    tw, _ = blf.dimensions(0, f"{r['token'].upper()}")
                    token_widths['C'] = max(token_widths.get('C', 0.0), tw)

                    # Label column (without toggle icon)
                    blf.size(0, body_size)
                    full_txt = r["label"]
                    if r.get("label_extra"):
                        full_txt += "  " + r["label_extra"]
                    
                    # Extract label without toggle icons
                    label_txt = full_txt
                    for toggle_icon in ["  󰨚", "  󰨙", "󰨚", "󰨙"]:
                        label_txt = label_txt.replace(toggle_icon, "")
                    label_txt = label_txt.rstrip()
                    
                    # Apply max_label_length truncation
                    if max_label_length > 0 and len(label_txt) > max_label_length:
                        if max_label_length > 3:
                            label_txt = label_txt[:max_label_length-3] + "..."
                        else:
                            label_txt = label_txt[:max_label_length]
                    
                    lw, _ = blf.dimensions(0, label_txt)
                    token_widths['L'] = max(token_widths.get('L', 0.0), lw)
                    
                    # Toggle column
                    if r.get("mapping_type") == "CONTEXT_TOGGLE":
                        blf.size(0, toggle_size)
                        tw_on, _ = blf.dimensions(0, "󰨚")
                        tw_off, _ = blf.dimensions(0, "󰨙")
                        toggle_w = max(tw_on, tw_off)
                        token_widths['T'] = max(token_widths.get('T', 0.0), toggle_w)
                
                blf.size(0, chord_size)

        # Build metrics dict with dynamic token widths
        metrics = {
            "token_widths": token_widths,  # Dict of token_type -> max_width
            "header": col_max_header_w,
            "has_icons": has_any_icon,
            # Legacy compatibility
            "chord_w": token_widths.get('C', 0.0),
            "label_w": token_widths.get('L', 0.0),
            "toggle_w": token_widths.get('T', 0.0),
            "icon_w": token_widths.get('I', 0.0),
            "token": token_widths.get('C', 0.0),
            "label": token_widths.get('L', 0.0),
            "label_base": token_widths.get('L', 0.0),
        }
        column_metrics.append(metrics)

    # Check footer items
    f_token_w = 0.0
    f_label_w = 0.0
    for r in footer:
        if r["kind"] == "hint":
            # Hint uses its raw text as token, label is empty
            tw, _ = blf.dimensions(0, r["token"])
            f_token_w = max(f_token_w, tw)
        else:
            tw, _ = blf.dimensions(0, f"<{r['token'].upper()}>")
            f_token_w = max(f_token_w, tw)

            blf.size(0, body_size)
            lw, _ = blf.dimensions(0, r["label"])
            f_label_w = max(f_label_w, lw)
            blf.size(0, chord_size)

    return column_metrics, {"token": f_token_w, "label": f_label_w}
