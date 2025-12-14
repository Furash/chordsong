import json
from dataclasses import dataclass


def get_str_attr(obj, attr, default=""):
    """Get string attribute with fallback and strip whitespace."""
    return (getattr(obj, attr, default) or default).strip()


def normalize_token(event_type: str):
    """
    Convert a Blender event.type into a chord token.
    Minimal rules:
    - Letters become lowercase.
    - Digits remain digits.
    - Ignore pure modifiers and non-keyboard noise.
    """
    if not event_type:
        return None

    if event_type in {"LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_CTRL", "RIGHT_CTRL", "LEFT_ALT", "RIGHT_ALT", "OSKEY"}:
        return None

    if len(event_type) == 1 and event_type.isalpha():
        return event_type.lower()

    if event_type.isdigit():
        return event_type

    # Common named keys (expand later)
    named = {
        "SPACE": "space",
        "TAB": "tab",
        "RET": "enter",
        "ESC": "esc",
        "BACK_SPACE": "backspace",
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
    try:
        v = json.loads(kwargs_json)
    except (ValueError, TypeError):
        return {}
    return v if isinstance(v, dict) else {}


