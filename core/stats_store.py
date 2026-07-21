"""Pure statistics logic: report parsing, count merging, JSON (de)serialization.

No bpy imports here — everything in this module is unit-testable outside
Blender (see tests/test_stats_store.py). The bpy-facing glue lives in
core/stats_manager.py.
"""

CATEGORIES = ("operators", "chords", "scripts", "properties")

_OPERATOR_REPORT_PREFIX = "bpy.ops."
_PROPERTY_REPORT_PREFIX = "bpy.context."

# Operators whose usage is tracked separately (chords) or is pure UI noise.
DEFAULT_EXCLUDED_PREFIXES = ("chordsong.",)

# Exact idnames never counted: text.run_script fires for every chordsong
# script execution (tracked in the "scripts" category instead).
DEFAULT_EXCLUDED_IDNAMES = frozenset({"text.run_script"})


def parse_operator_report(message: str, excluded_prefixes=DEFAULT_EXCLUDED_PREFIXES):
    """Extract an operator idname from an OPERATOR report message.

    Report messages look like "bpy.ops.mesh.primitive_cube_add(size=2, ...)".
    Returns "mesh.primitive_cube_add", or None when the message is not an
    operator call or the idname is excluded.
    """
    if not message or not message.startswith(_OPERATOR_REPORT_PREFIX):
        return None
    head = message[len(_OPERATOR_REPORT_PREFIX):]
    paren = head.find("(")
    if paren <= 0:
        return None
    idname = head[:paren].strip()
    module, dot, op_name = idname.partition(".")
    if not dot or not module or not op_name or "." in op_name:
        return None
    if idname in DEFAULT_EXCLUDED_IDNAMES:
        return None
    for prefix in excluded_prefixes:
        if idname.startswith(prefix):
            return None
    return idname


def parse_property_report(message: str):
    """Extract (path, value) from a PROPERTY report message.

    Report messages look like "bpy.context.space_data.clip_end = 996.7".
    The path is returned relative to bpy.context ("space_data.clip_end"),
    matching the context_path form used by CONTEXT_PROPERTY mappings.
    Returns None for anything else (bpy.data assignments, malformed lines).
    """
    if not message or not message.startswith(_PROPERTY_REPORT_PREFIX):
        return None
    head = message[len(_PROPERTY_REPORT_PREFIX):]
    path, sep, value = head.partition(" = ")
    path = path.strip()
    if not sep or not path:
        return None
    return path, value.strip()


def normalize_count(value) -> int:
    """Return count as int; tolerates the legacy dict format {"count": n}."""
    if isinstance(value, dict):
        value = value.get("count", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def normalize_operator_idname(name: str) -> str:
    """Convert legacy class-name keys ("VIEW3D_OT_move") to idnames ("view3d.move").

    Stats files written by earlier prototypes stored operator class names;
    current capture stores idnames. Already-dotted names pass through.
    """
    if "_OT_" in name and "." not in name:
        module, _, op_name = name.partition("_OT_")
        if module and op_name:
            return f"{module.lower()}.{op_name.lower()}"
    return name


def data_to_counts(data: dict) -> dict:
    """Build {"operators": {...}, "chords": {...}} from loaded JSON data.

    Migrates legacy operator keys to idname form (merging counts when both
    forms exist) and drops excluded operators recorded by earlier prototypes.
    """
    counts = {}
    for category in CATEGORIES:
        raw = data.get(category)
        if not isinstance(raw, dict):
            counts[category] = {}
            continue
        cat = {}
        for key, value in raw.items():
            if category == "operators":
                key = normalize_operator_idname(key)
                if key in DEFAULT_EXCLUDED_IDNAMES:
                    continue
                if any(key.startswith(p) for p in DEFAULT_EXCLUDED_PREFIXES):
                    continue
            cat[key] = cat.get(key, 0) + normalize_count(value)
        counts[category] = cat
    return counts


def merge_counts(base: dict, extra: dict) -> dict:
    """Sum two per-category count mappings without mutating either."""
    merged = {}
    for category in CATEGORIES:
        cat = dict(base.get(category, {}))
        for name, value in extra.get(category, {}).items():
            cat[name] = normalize_count(cat.get(name, 0)) + normalize_count(value)
        merged[category] = cat
    return merged


def counts_to_data(counts: dict, blacklist=None, last_saved: str = "", property_values=None) -> dict:
    """Build the JSON-serializable stats file structure."""
    data = {category: dict(counts.get(category, {})) for category in CATEGORIES}
    data["_metadata"] = {
        "last_saved": last_saved,
        "blacklist": sorted(blacklist) if blacklist else [],
        "property_values": dict(property_values) if property_values else {},
    }
    return data


def blacklist_key(category: str, name: str) -> str:
    return f"{category}:{name}"


def parse_blacklist(raw_json: str) -> set:
    """Parse the prefs blacklist JSON string into a set of keys."""
    import json

    try:
        items = json.loads(raw_json or "[]")
        return {str(i) for i in items} if isinstance(items, list) else set()
    except (ValueError, TypeError):
        return set()


def dump_blacklist(keys) -> str:
    import json

    return json.dumps(sorted(keys))
