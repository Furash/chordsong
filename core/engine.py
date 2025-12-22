import json
from dataclasses import dataclass

def get_str_attr(obj, attr, default=""):
    """Get string attribute with fallback and strip whitespace."""
    return (getattr(obj, attr, default) or default).strip()

def normalize_token(event_type: str, shift: bool = False):
    """
    Convert a Blender event.type into a chord token.
    Minimal rules:
    - Letters: lowercase by default, uppercase if shift is pressed.
    - Digits remain digits.
    - Ignore pure modifiers and non-keyboard noise.

    Args:
        event_type: The Blender event type string
        shift: Whether shift key is pressed
    """
    if not event_type:
        return None

    if event_type in {"LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_CTRL", "RIGHT_CTRL", "LEFT_ALT", "RIGHT_ALT", "OSKEY"}:
        return None

    if len(event_type) == 1 and event_type.isalpha():
        # Return uppercase if shift is pressed, lowercase otherwise
        return event_type.upper() if shift else event_type.lower()

    if event_type.isdigit():
        return event_type

    # Common named keys (expand later)
    named = {
        "SPACE": "space",
        "TAB": "tab",
        "RET": "enter",
        "ESC": "esc",
        "BACK_SPACE": "backspace",
        # Number keys (main row) - with shift support for symbols
        "ZERO": ")" if shift else "0",
        "ONE": "!" if shift else "1",
        "TWO": "@" if shift else "2",
        "THREE": "#" if shift else "3",
        "FOUR": "$" if shift else "4",
        "FIVE": "%" if shift else "5",
        "SIX": "^" if shift else "6",
        "SEVEN": "&" if shift else "7",
        "EIGHT": "*" if shift else "8",
        "NINE": "(" if shift else "9",
        # Numpad keys (prefixed with 'n')
        "NUMPAD_0": "n0",
        "NUMPAD_1": "n1",
        "NUMPAD_2": "n2",
        "NUMPAD_3": "n3",
        "NUMPAD_4": "n4",
        "NUMPAD_5": "n5",
        "NUMPAD_6": "n6",
        "NUMPAD_7": "n7",
        "NUMPAD_8": "n8",
        "NUMPAD_9": "n9",
        # Common punctuation (with shift support)
        "MINUS": "_" if shift else "-",
        "EQUAL": "+" if shift else "=",
        "LEFT_BRACKET": "{" if shift else "[",
        "RIGHT_BRACKET": "}" if shift else "]",
        "SEMI_COLON": ":" if shift else ";",
        "QUOTE": '"' if shift else "'",
        "COMMA": "<" if shift else ",",
        "PERIOD": ">" if shift else ".",
        "SLASH": "?" if shift else "/",
        "BACK_SLASH": "|" if shift else "\\",
        "GRAVE_ACCENT": "~" if shift else "grave",
        "ACCENT_GRAVE": "~" if shift else "grave",  # Blender uses ACCENT_GRAVE
    }
    return named.get(event_type, None)

def split_chord(chord: str):
    return [t for t in (chord or "").strip().split() if t]

@dataclass(frozen=True)
class Candidate:
    next_token: str
    label: str
    group: str
    icon: str = ""
    is_final: bool = False  # True if this is the last token in the chord

def build_match_sets(mappings):
    """
    Returns (exact_set, prefix_set) of token tuples.
    prefix_set contains all proper prefixes of any mapping chord.
    """
    exact = set()
    prefixes = set()
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue
        chord_tokens = tuple(split_chord(get_str_attr(m, "chord")))
        if not chord_tokens:
            continue
        exact.add(chord_tokens)
        for i in range(1, len(chord_tokens)):
            prefixes.add(chord_tokens[:i])
    return exact, prefixes

def find_exact_mapping(mappings, buffer_tokens):
    bt = tuple(buffer_tokens)
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue
        if tuple(split_chord(get_str_attr(m, "chord"))) == bt:
            return m
    return None

def candidates_for_prefix(mappings, buffer_tokens):
    """
    For the current prefix, list the next possible token(s) and labels.
    For a chord 'g g' and prefix ['g'], candidate is next_token='g'.
    """
    bt = tuple(buffer_tokens)
    out = {}
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue

        # Skip chordsong.recents operator - it's only shown in footer
        if getattr(m, "mapping_type", "") == "OPERATOR":
            operator = get_str_attr(m, "operator")
            if operator == "chordsong.recents":
                continue

        tokens = split_chord(get_str_attr(m, "chord"))
        if not tokens:
            continue
        if bt and tuple(tokens[: len(bt)]) != bt:
            continue
        if len(tokens) <= len(bt):
            continue
        nxt = tokens[len(bt)]
        label = get_str_attr(m, "label") or "(missing label)"
        group = get_str_attr(m, "group")
        icon = get_str_attr(m, "icon")
        # Check if this is the final token in the chord
        is_final = len(tokens) == len(bt) + 1
        # Keep first label per next token for minimal UI
        if nxt not in out:
            out[nxt] = Candidate(nxt, label, group, icon, is_final)
        elif not out[nxt].is_final and is_final:
            # If we already have a non-final candidate, but found a final one, update it
            out[nxt] = Candidate(nxt, label, group, icon, is_final)
    return list(out.values())

def parse_kwargs(kwargs_json: str) -> dict:
    if not (kwargs_json or "").strip():
        return {}

    # Try JSON format first
    try:
        v = json.loads(kwargs_json)
        return v if isinstance(v, dict) else {}
    except (ValueError, TypeError):
        pass

    # Try Python-like format: key = value, key2 = value2
    try:
        import ast
        import re

        # If it's a full bpy.ops call, extract just the part inside ()
        k_strip = kwargs_json.strip()
        if "(" in k_strip and k_strip.endswith(")") and not k_strip.startswith("("):
            # Stricter check: must look like a function call and not just property assignments
            # A full call shouldn't have an '=' before the first '('
            first_paren = k_strip.find("(")
            prefix = k_strip[:first_paren].strip()
            
            # If it's a full call, the prefix should be a valid python identifier/path
            # and there should be no '=' in the prefix (which would mean it's an assignment)
            if "=" not in prefix and "." in prefix:
                if any(prefix.startswith(p) for p in ("bpy.", "ops.", "bpy.ops.")) or " " not in prefix:
                    inner_match = re.search(r'\((.*)\)', k_strip)
                    if inner_match:
                        kwargs_json = inner_match.group(1)

        # Parse Python-like assignment format
        result = {}
        # Split by commas, but respect quoted strings and nested brackets/parens
        parts = []
        current = []
        in_quotes = False
        quote_char = ''
        nesting_level = 0
        
        for char in kwargs_json:
            if char in ('"', "'"):
                if not in_quotes:
                    in_quotes = True
                    quote_char = char
                elif char == quote_char:
                    in_quotes = False
            
            if not in_quotes:
                if char in ('(', '[', '{'):
                    nesting_level += 1
                elif char in (')', ']', '}'):
                    nesting_level -= 1
            
            if char == ',' and not in_quotes and nesting_level == 0:
                parts.append(''.join(current).strip())
                current = []
            else:
                current.append(char)
        
        if current:
            parts.append(''.join(current).strip())

        # Parse each key = value pair
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                key = key.strip()
                value = value.strip()

                # Try to evaluate the value safely using ast.literal_eval
                try:
                    result[key] = ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    # Keep as string if can't evaluate (strip extra quotes)
                    result[key] = value.strip('"\'')

        return result
    except Exception:
        return {}

def filter_mappings_by_context(mappings, context_type: str):
    """
    Filter mappings by editor context.

    Args:
        mappings: Collection of mapping objects
        context_type: One of "VIEW_3D", "GEOMETRY_NODE", "SHADER_EDITOR", "IMAGE_EDITOR"

    Returns:
        List of mappings matching the context
    """
    filtered = []
    for m in mappings:
        # Get the context attribute, default to VIEW_3D for backward compatibility
        mapping_context = getattr(m, "context", "VIEW_3D")
        if mapping_context == context_type:
            filtered.append(m)
    return filtered

def get_leader_key_type() -> str:
    """Get the current leader key type from the addon keymap.

    Returns:
        The Blender key type string (e.g., "SPACE", "ACCENT_GRAVE")
    """
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            return "SPACE"

        km = kc.keymaps.get("3D View")
        if not km:
            return "SPACE"

        # Find the leader keymap item
        for kmi in km.keymap_items:
            if kmi.idname == "chordsong.leader":
                return kmi.type

        return "SPACE"
    except Exception:
        return "SPACE"

def get_leader_key_token() -> str:
    """Get the current leader key as a display token.

    Returns:
        A human-readable token string for display (e.g., "space", "grave")
    """
    try:
        import bpy  # type: ignore
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
                shift_state = getattr(kmi, "shift", False)
                token = normalize_token(kmi.type, shift=shift_state)
                if token:
                    return token
                # Fallback: use key type directly
                if kmi.type:
                    return kmi.type.lower()
                return "<Leader>"

        return "<Leader>"
    except Exception:
        return "<Leader>"

def set_leader_key_in_keymap(key_type: str):
    """Set the leader key type in all addon keymaps.

    Args:
        key_type: Blender key type string (e.g., "SPACE", "ACCENT_GRAVE")
    """
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.addon
        if not kc:
            return

        # Update leader key in all registered keymaps
        keymap_names = ["3D View", "Node Editor", "Image Editor"]
        for km_name in keymap_names:
            km = kc.keymaps.get(km_name)
            if km:
                for kmi in km.keymap_items:
                    if kmi.idname == "chordsong.leader":
                        kmi.type = key_type
                        break
    except Exception:
        pass
