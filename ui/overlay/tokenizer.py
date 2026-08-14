"""Format string tokenizer for overlay display."""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Token:
    """Represents a single token in the format string."""
    type: str  # 'I', 'C', 'G', 'g', 'i', 'L', 'N', 'n', 'S', 's', 'T'
    content: str  # The actual text content to display
    color_key: str  # Key to look up color in preferences

def split_group_path(name: str) -> List[str]:
    """Split a group name into hierarchy tokens on '|' (issue #18).

    "HardSurface | Kushiro" -> ["HardSurface", "Kushiro"]. Flat names
    yield a single token; blank names yield [].
    """
    return [t.strip() for t in (name or "").split("|") if t.strip()]

def common_prefix_len(group_names) -> int:
    """Longest common token-prefix length across group names at a level.

    Blank names are ignored. Used to drop already-traversed hierarchy
    levels from overlay group display.
    """
    paths = [p for p in (split_group_path(g) for g in group_names) if p]
    if not paths:
        return 0
    n = 0
    for tokens in zip(*paths):
        if any(t != tokens[0] for t in tokens):
            break
        n += 1
    return n

def _display_groups(groups: List[str], prefix_len: int) -> List[str]:
    """Level-relative display tokens: drop the common prefix (always
    keeping the last token), dedupe preserving order."""
    seen = set()
    out = []
    for g in groups:
        tokens = split_group_path(g)
        if not tokens:
            continue
        name = tokens[min(prefix_len, len(tokens) - 1)]
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out

def parse_format_string(format_str: str) -> List[str]:
    """Parse format string into list of token types.
    
    Args:
        format_str: Format string like "C G S N" or "I L"
    
    Returns:
        List of token type strings like ['C', 'G', 'S', 'N']
    """
    # Split by whitespace and filter empty strings
    tokens = [t.strip() for t in format_str.split() if t.strip()]
    return tokens

def generate_tokens_for_folder(
    token_types: List[str],
    chord: str,
    icon: str,
    groups: List[str],
    count: int,
    separator_a: str,
    separator_b: str,
    group_icons: Optional[dict] = None,
    group_prefix_len: int = 0,
) -> List[Token]:
    """Generate tokens for a folder item (multiple keymaps).
    
    Args:
        token_types: List of token type strings from format string
        chord: Chord token (e.g., "a")
        icon: Icon character
        groups: List of group names
        count: Number of keymaps in this folder
        separator_a: Primary separator string
        separator_b: Secondary separator string
    
    Returns:
        List of Token objects with content and color keys
    """
    tokens = []
    
    for token_type in token_types:
        if token_type == 'I':
            # Icon
            if icon:
                tokens.append(Token(type='I', content=icon, color_key='overlay_color_icon'))
        
        elif token_type == 'C':
            # Chord
            tokens.append(Token(type='C', content=chord, color_key='overlay_color_chord'))
        
        elif token_type == 'G':
            # All groups, level-relative (or first 2 + ellipsis)
            groups_str = _format_groups_all(groups, group_prefix_len)
            if groups_str:
                tokens.append(Token(type='G', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'g':
            # First group only, level-relative
            groups_str = _format_groups_first(groups, group_prefix_len)
            if groups_str:
                tokens.append(Token(type='g', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'G*':
            # All groups, full paths (no level trimming)
            groups_str = _format_groups_all_full(groups)
            if groups_str:
                tokens.append(Token(type='G*', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'g*':
            # First group only, full path (no level trimming)
            groups_str = _format_groups_first_full(groups)
            if groups_str:
                tokens.append(Token(type='g*', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'i':
            # Group icon (first group's icon)
            if groups and group_icons:
                first_group = groups[0] if groups else None
                if first_group and first_group in group_icons:
                    group_icon = group_icons[first_group]
                    if group_icon:
                        tokens.append(Token(type='i', content=group_icon, color_key='overlay_color_group'))

        elif token_type == 'L':
            # Label - not typically used for folders, but we can show something
            tokens.append(Token(type='L', content="", color_key='overlay_color_label'))
        
        elif token_type == 'N':
            # Verbose count: "+3 keymaps"
            suffix = "s" if count > 1 else ""
            content = f"+{count} keymap{suffix}"
            tokens.append(Token(type='N', content=content, color_key='overlay_color_counter'))
        
        elif token_type == 'n':
            # Compact count: "+3"
            content = f"+{count}"
            tokens.append(Token(type='n', content=content, color_key='overlay_color_counter'))
        
        elif token_type == 'S':
            # Separator A
            tokens.append(Token(type='S', content=separator_a, color_key='overlay_color_separator'))
        
        elif token_type == 's':
            # Separator B (secondary)
            tokens.append(Token(type='s', content=separator_b, color_key='overlay_color_separator'))
        
        elif token_type == 'T':
            # Toggle token - not applicable for folders, skip
            pass
    
    return tokens

def generate_tokens_for_item(
    token_types: List[str],
    chord: str,
    icon: str,
    groups: List[str],
    label: str,
    separator_a: str,
    separator_b: str,
    mapping_type: Optional[str] = None,
    group_icons: Optional[dict] = None,
    group_prefix_len: int = 0,
) -> List[Token]:
    """Generate tokens for a single item.
    
    Args:
        token_types: List of token type strings from format string
        chord: Chord token (e.g., "a")
        icon: Icon character
        groups: List of group names
        label: Label text
        separator_a: Primary separator string
        separator_b: Secondary separator string
        mapping_type: Type of mapping (for special handling)
    
    Returns:
        List of Token objects with content and color keys
    """
    tokens = []
    
    for token_type in token_types:
        if token_type == 'I':
            # Icon
            if icon:
                tokens.append(Token(type='I', content=icon, color_key='overlay_color_icon'))
        
        elif token_type == 'C':
            # Chord
            tokens.append(Token(type='C', content=chord, color_key='overlay_color_chord'))
        
        elif token_type == 'G':
            # All groups, level-relative (or first 2 + ellipsis)
            groups_str = _format_groups_all(groups, group_prefix_len)
            if groups_str:
                tokens.append(Token(type='G', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'g':
            # First group only, level-relative
            groups_str = _format_groups_first(groups, group_prefix_len)
            if groups_str:
                tokens.append(Token(type='g', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'G*':
            # All groups, full paths (no level trimming)
            groups_str = _format_groups_all_full(groups)
            if groups_str:
                tokens.append(Token(type='G*', content=groups_str, color_key='overlay_color_group'))

        elif token_type == 'g*':
            # First group only, full path (no level trimming)
            groups_str = _format_groups_first_full(groups)
            if groups_str:
                tokens.append(Token(type='g*', content=groups_str, color_key='overlay_color_group'))
        
        elif token_type == 'i':
            # Group icon (first group's icon)
            if groups and group_icons:
                first_group = groups[0] if groups else None
                if first_group and first_group in group_icons:
                    group_icon = group_icons[first_group]
                    if group_icon:
                        tokens.append(Token(type='i', content=group_icon, color_key='overlay_color_group'))
        
        elif token_type == 'L':
            # Label - remove toggle icons if present (they should be in 'T' token)
            clean_label = label
            for toggle_icon in ["  󰨚", "  󰨙", "󰨚", "󰨙"]:
                clean_label = clean_label.replace(toggle_icon, "")
            clean_label = clean_label.rstrip()
            tokens.append(Token(type='L', content=clean_label, color_key='overlay_color_label'))
        
        elif token_type == 'N' or token_type == 'n':
            # Count tokens don't make sense for single items, skip
            pass
        
        elif token_type == 'S':
            # Separator A
            tokens.append(Token(type='S', content=separator_a, color_key='overlay_color_separator'))
        
        elif token_type == 's':
            # Separator B (secondary)
            tokens.append(Token(type='s', content=separator_b, color_key='overlay_color_separator'))
        
        elif token_type == 'T':
            # Toggle icon - check if this is a toggle item
            if mapping_type == "CONTEXT_TOGGLE":
                # Detect toggle state from label if present
                # This is a bit hacky - we check if label contains toggle icons
                # In the future, toggle state should be passed as a separate parameter
                toggle_icon = "󰨚"  # Default to ON
                if "󰨙" in label:
                    toggle_icon = "󰨙"  # OFF
                elif "󰨚" in label:
                    toggle_icon = "󰨚"  # ON
                
                tokens.append(Token(type='T', content=toggle_icon, color_key='overlay_color_toggle_on'))
    
    return tokens

def _format_groups_all(groups: List[str], prefix_len: int = 0) -> str:
    """Format all groups level-relative (up to 2 distinct, then ellipsis)."""
    display = _display_groups(groups, prefix_len)
    if not display:
        return "(unlabeled)"

    groups_str = ", ".join(display[:2])
    if len(display) > 2:
        groups_str += "..."

    return groups_str

def _format_groups_first(groups: List[str], prefix_len: int = 0) -> str:
    """Format first group only, level-relative."""
    display = _display_groups(groups, prefix_len)
    if not display:
        return "(unlabeled)"

    return display[0]

def _format_groups_all_full(groups: List[str]) -> str:
    """Format all groups as full paths (G* token; pre-#18 G behavior)."""
    if not groups:
        return "(unlabeled)"

    groups_str = ", ".join(groups[:2])
    if len(groups) > 2:
        groups_str += "..."

    return groups_str

def _format_groups_first_full(groups: List[str]) -> str:
    """Format first group as full path (g* token; pre-#18 g behavior)."""
    if not groups:
        return "(unlabeled)"

    return groups[0]

def tokens_to_display_parts(tokens: List[Token]) -> tuple[str, str]:
    """Convert tokens to display parts (base and extra) for backward compatibility.
    
    This is used to maintain compatibility with the current two-part rendering system.
    
    Args:
        tokens: List of Token objects
    
    Returns:
        Tuple of (base_text, extra_text) - extra_text can be empty
    """
    if not tokens:
        return "", ""
    
    # For now, just join all tokens with spaces for base
    # In the future, we can make this more sophisticated
    parts = [t.content for t in tokens if t.content]
    return "  ".join(parts), ""
