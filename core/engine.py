import json
from dataclasses import dataclass

def get_str_attr(obj, attr, default=""):
    """Get string attribute with fallback and strip whitespace."""
    return (getattr(obj, attr, default) or default).strip()

def normalize_token(event_type: str, shift: bool = False, ctrl: bool = False, alt: bool = False, oskey: bool = False, mod_side: str = None):
    """
    Convert a Blender event into a chord token using AHK-style modifier symbols.

    Symbols:
    ^ : Ctrl
    ! : Alt
    + : Shift
    # : Win (OSKey)
    < : Left modifier prefix (e.g., <^ for LCtrl)
    > : Right modifier prefix (e.g., >! for RAlt)
    """
    if not event_type:
        return None

    # Ignore pure modifiers as tokens
    if event_type in {
        "LEFT_SHIFT", "RIGHT_SHIFT",
        "LEFT_CTRL", "RIGHT_CTRL",
        "LEFT_ALT", "RIGHT_ALT",
        "OSKEY"
    }:
        return None

    # Get the base key name (lower case, no shift applied yet)
    base = None
    if len(event_type) == 1 and event_type.isalpha():
        base = event_type.lower()
    elif event_type.isdigit():
        base = event_type
    else:
        # Common named keys - always use the base (unshifted) key name
        named = {
            "SPACE": "space",
            "TAB": "tab",
            "RET": "enter",
            "ESC": "esc",
            "BACK_SPACE": "backspace",
            # Number keys (main row)
            "ZERO": "0", "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4",
            "FIVE": "5", "SIX": "6", "SEVEN": "7", "EIGHT": "8", "NINE": "9",
            # Numpad keys
            "NUMPAD_0": "n0", "NUMPAD_1": "n1", "NUMPAD_2": "n2", "NUMPAD_3": "n3",
            "NUMPAD_4": "n4", "NUMPAD_5": "n5", "NUMPAD_6": "n6", "NUMPAD_7": "n7",
            "NUMPAD_8": "n8", "NUMPAD_9": "n9",
            # Common punctuation
            "MINUS": "-", "EQUAL": "=",
            "LEFT_BRACKET": "[", "RIGHT_BRACKET": "]",
            "SEMI_COLON": ";", "QUOTE": "'",
            "COMMA": ",", "PERIOD": ".",
            "SLASH": "/", "BACK_SLASH": "\\",
            "GRAVE_ACCENT": "grave", "ACCENT_GRAVE": "grave",
            "NUM_LOCK": "numlock", "CAPS_LOCK": "capslock",
            # Arrows
            "UP_ARROW": "up", "DOWN_ARROW": "down",
            "LEFT_ARROW": "left", "RIGHT_ARROW": "right",
            # Navigation
            "PAGE_UP": "pageup", "PAGE_DOWN": "pagedown",
            "HOME": "home", "END": "end",
            "INSERT": "insert", "DEL": "delete",
            # Function keys F1 - F24
            "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
            "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
            "F13": "f13", "F14": "f14", "F15": "f15", "F16": "f16", "F17": "f17", "F18": "f18",
            "F19": "f19", "F20": "f20", "F21": "f21", "F22": "f22", "F23": "f23", "F24": "f24",
            # Numpad Operators
            "NUMPAD_SLASH": "n/", "NUMPAD_ASTERISK": "n*",
            "NUMPAD_MINUS": "n-", "NUMPAD_PLUS": "n+",
            "NUMPAD_ENTER": "nenter", "NUMPAD_PERIOD": "n.",
            # Mouse buttons 1-7
            "LEFTMOUSE": "m1", "RIGHTMOUSE": "m2", "MIDDLEMOUSE": "m3",
            "BUTTON4MOUSE": "m4", "BUTTON5MOUSE": "m5", "BUTTON6MOUSE": "m6",
            "BUTTON7MOUSE": "m7",
            # Mouse wheel
            "WHEELUPMOUSE": "mwu", "WHEELDOWNMOUSE": "mwd",
        }
        base = named.get(event_type, None)

    if base is None:
        return None

    # Build modifier prefix
    mods = ""

    # OSKey (Windows/Cmd)
    if oskey:
        mods += "#"

    # Ctrl
    if ctrl:
        if mod_side == "LEFT":
            mods += "<^"
        elif mod_side == "RIGHT":
            mods += ">^"
        else:
            mods += "^"

    # Alt
    if alt:
        if mod_side == "LEFT":
            mods += "<!"
        elif mod_side == "RIGHT":
            mods += ">!"
        else:
            mods += "!"

    # Shift
    if shift:
        if mod_side == "LEFT":
            mods += "<+"
        elif mod_side == "RIGHT":
            mods += ">+"
        else:
            mods += "+"

    return mods + base

def split_chord(chord: str):
    return [t for t in (chord or "").strip().split() if t]

@dataclass(frozen=True)
class Candidate:
    next_token: str
    label: str
    group: str
    icon: str = ""
    is_final: bool = False  # True if this is the last token in the chord
    mapping_type: str = "OPERATOR"
    property_value: str = ""
    count: int = 1          # Number of mappings reachable through this token
    groups: tuple[str, ...] = () # Unique groups reachable through this token

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

def _get_token_parts(token: str) -> tuple[set[str], str]:
    """Split a token into a set of modifiers and a base key."""
    mod_symbols = {'#', '^', '!', '+'}
    found_mods = set()
    res = token

    i = 0
    while i < len(res):
        char = res[i]
        if char in mod_symbols:
            found_mods.add(char)
            i += 1
        elif (char == '<' or char == '>') and i + 1 < len(res) and res[i+1] in mod_symbols:
            # Side-specific modifier (e.g. <^ )
            found_mods.add(res[i:i+2])
            i += 2
        else:
            break

    base = res[i:]
    # Accept common aliases for the Grave/Tilde key so users can type either form:
    # - ` / backtick  == grave
    # - ~ / tilde     == +grave
    if base in ("`", "backtick"):
        base = "grave"
    elif base in ("~", "tilde"):
        found_mods.add('+')
        base = "grave"
    # Accept common shifted punctuation aliases (users may type the literal character
    # instead of the canonical "+<base>" form):
    # - <  == +,
    # - >  == +.
    # - :  == +;
    # - "  == +'
    # - {  == +[
    # - }  == +]
    # - ?  == +/
    # - |  == +\
    _shifted_punct_aliases = {
        "<": ",",
        ">": ".",
        ":": ";",
        '"': "'",
        "{": "[",
        "}": "]",
        "?": "/",
        "|": "\\",
    }
    if base in _shifted_punct_aliases:
        found_mods.add('+')
        base = _shifted_punct_aliases[base]
    # If base is a single uppercase letter, it implies a shift modifier
    if len(base) == 1 and base.isupper():
        found_mods.add('+')
        base = base.lower()

    return found_mods, base

def tokens_match(mapping_token: str, pressed_token: str) -> bool:
    """Check if a mapping token matches a pressed token, handling AHK modifiers and order."""
    if mapping_token == pressed_token:
        return True

    m_mods, m_base = _get_token_parts(mapping_token)
    p_mods, p_base = _get_token_parts(pressed_token)

    if m_base != p_base:
        return False

    # If the mapping doesn't have side indicators (< or >), we allow it to match
    # any side of that modifier in the pressed token.
    has_m_side = any(('<' in m or '>' in m) for m in m_mods)

    if not has_m_side:
        # Strip side indicators from pressed mods for comparison
        stripped_p_mods = {mod.replace('<', '').replace('>', '') for mod in p_mods}
        return m_mods == stripped_p_mods

    # If mapping HAS side indicators, they must match exactly
    return m_mods == p_mods

def humanize_token(token: str) -> str:
    """Convert an internal AHK-style token to a more readable format for the user."""
    # Mapping table for modifiers
    mod_map = {
        '^': 'Ctrl',
        '!': 'Alt',
        '+': 'Shift',
        '#': 'Win'
    }

    # Process side indicators and modifiers
    res = token
    parts = []

    # Loop to pull off potential <^ >! etc prefixes
    while len(res) > 0:
        side = ""
        if res.startswith('<'):
            # Left is default, show no prefix
            side = ""
            res = res[1:]
        elif res.startswith('>'):
            side = "R"
            res = res[1:]

        if len(res) > 0 and res[0] in mod_map:
            parts.append(f"{side}{mod_map[res[0]]}")
            res = res[1:]
        else:
            # Reached the base key
            # If we had a side indicator with no modifier, put it back or ignore
            # but usually it's tied to one.
            parts.append(res)
            break

    return "+".join(parts)

def humanize_chord(tokens: list[str]) -> str:
    """Convert a list of tokens into a readable chord string."""
    return " ".join(humanize_token(t) for t in tokens)

def find_exact_mapping(mappings, buffer_tokens):
    bt = tuple(buffer_tokens)
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue
        chord_tokens = split_chord(get_str_attr(m, "chord"))
        if len(chord_tokens) != len(bt):
            continue

        if all(tokens_match(m_tok, b_tok) for m_tok, b_tok in zip(chord_tokens, bt)):
            return m
    return None

def candidates_for_prefix(mappings, buffer_tokens, context=None):
    """
    For the current prefix, list the next possible token(s) and labels.
    """
    bt = tuple(buffer_tokens)
    out = {}
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue

        # Skip chordsong.recents operator
        mapping_type = get_str_attr(m, "mapping_type", "OPERATOR")
        if mapping_type == "OPERATOR":
            operator = get_str_attr(m, "operator")
            if operator == "chordsong.recents":
                continue

        tokens = split_chord(get_str_attr(m, "chord"))
        if not tokens:
            continue

        # Check if the current buffer matches the chord prefix
        if bt:
            if len(tokens) <= len(bt):
                continue
            if not all(tokens_match(m_tok, b_tok) for m_tok, b_tok in zip(tokens[:len(bt)], bt)):
                continue

        if len(tokens) <= len(bt):
            continue

        nxt = tokens[len(bt)]
        label = get_str_attr(m, "label") or "(missing label)"
        group = get_str_attr(m, "group")
        icon = get_str_attr(m, "icon")
        property_value = get_str_attr(m, "property_value")

        # Determine dynamic toggle state if possible
        if context and mapping_type == "CONTEXT_TOGGLE":
            try:
                path = get_str_attr(m, "context_path")
                # Very basic evaluation - match the logic used in toggle execution
                if path:
                    # Resolve path against context (same logic as do_toggle_path)
                    obj = context
                    parts = path.split(".")
                    for part in parts[:-1]:
                        next_obj = getattr(obj, part, None)
                        if next_obj is None:
                            # Path resolution failed, fallback to switch icon
                            raise AttributeError(f"Could not resolve path part: {part}")
                        obj = next_obj
                    prop_name = parts[-1]
                    if not hasattr(obj, prop_name):
                        # Property doesn't exist, fallback to switch icon
                        raise AttributeError(f"Property not found: {prop_name}")
                    val = getattr(obj, prop_name)
                    if not isinstance(val, bool):
                        # Not a boolean, fallback to switch icon
                        raise TypeError(f"Property is not boolean: {prop_name}")
                    # User icons: 󰨙 (off) and 󰨚 (on/switch)
                    if bool(val):
                        label = f"{label}  󰨚"
                    else:
                        label = f"{label}  󰨙"
            except (AttributeError, TypeError, ReferenceError):
                # Path resolution failed or property doesn't exist, fallback to switch icon
                label = f"{label}  󰨚"
            except Exception:
                # Other errors, fallback to switch icon
                label = f"{label}  󰨚"
        elif mapping_type == "CONTEXT_TOGGLE":
             label = f"{label}  󰨚"
        elif mapping_type == "CONTEXT_PROPERTY":
            if property_value:
                # Store it in label so layout can decide how to split it
                # or better, just use a separator that layout/render understands
                label = f"{label}::  {property_value}"

        # Check if this is the final token in the chord
        is_final = len(tokens) == len(bt) + 1
        # Track counts and keep first label per next token for minimal UI
        if nxt not in out:
            out[nxt] = {
                "cand": Candidate(nxt, label, group, icon, is_final, mapping_type, property_value),
                "count": 1,
                "groups": {group} if group else set()
            }
        else:
            out[nxt]["count"] += 1
            if group:
                out[nxt]["groups"].add(group)

            # If we already have a non-final candidate, but found a final one, update the candidate
            # but keep the accumulated count and groups
            if not out[nxt]["cand"].is_final and is_final:
                out[nxt]["cand"] = Candidate(nxt, label, group, icon, is_final, mapping_type, property_value)

    # Convert back to Candidate list with updated counts
    result = []
    for token, data in out.items():
        c = data["cand"]
        result.append(Candidate(
            next_token=c.next_token,
            label=c.label,
            group=c.group,
            icon=c.icon,
            is_final=c.is_final,
            mapping_type=c.mapping_type,
            property_value=c.property_value,
            count=data["count"],
            groups=tuple(sorted(data["groups"]))
        ))
    return result

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

        # Parse Python-like assignment format: key = value, key2 = value2
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
        List of mappings matching the context (includes mappings with "ALL" context)
    """
    filtered = []
    for m in mappings:
        # Get the context attribute, default to VIEW_3D for backward compatibility
        mapping_context = getattr(m, "context", "VIEW_3D")
        # Include mappings with "ALL" context or matching context
        if mapping_context == context_type or mapping_context == "ALL":
            filtered.append(m)
    return filtered

def get_leader_key_type():
    """Get the current leader key type from the addon keymap.

    Returns:
        The Blender key type string (e.g., "SPACE", "ACCENT_GRAVE")
    """
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager

        # Check user keyconfig first (contains user customizations that persist)
        # Then fall back to addon keyconfig (default)
        keyconfigs = [wm.keyconfigs.user, wm.keyconfigs.addon]

        for kc in keyconfigs:
            if not kc:
                continue

            km = kc.keymaps.get("3D View")
            if not km:
                continue

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

        # Check user keyconfig first (contains user customizations that persist)
        # Then fall back to addon keyconfig (default)
        keyconfigs = [wm.keyconfigs.user, wm.keyconfigs.addon]

        for kc in keyconfigs:
            if not kc:
                continue

            km = kc.keymaps.get("3D View")
            if not km:
                continue

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

        # Update in both addon and user keyconfigs to ensure persistence
        # User changes will be stored in keyconfigs.user automatically
        keyconfigs = [wm.keyconfigs.addon, wm.keyconfigs.user]

        # Update leader key in all registered keymaps
        keymap_names = ["3D View", "Node Editor", "Image"]
        for kc in keyconfigs:
            if not kc:
                continue

            for km_name in keymap_names:
                km = kc.keymaps.get(km_name)
                if km:
                    for kmi in km.keymap_items:
                        if kmi.idname == "chordsong.leader":
                            kmi.type = key_type
                            break
    except Exception:
        pass
