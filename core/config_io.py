import json

# pylint: disable=broad-exception-caught


CONFIG_VERSION = 1


def dump_prefs(prefs) -> dict:
    """Serialize addon preferences to a JSON-serializable dict."""
    mappings = []
    for m in getattr(prefs, "mappings", []):
        kwargs_json = (getattr(m, "kwargs_json", "{}") or "{}").strip()
        kwargs_obj = {}
        try:
            parsed = json.loads(kwargs_json)
            if isinstance(parsed, dict):
                kwargs_obj = parsed
        except Exception:
            kwargs_obj = {}

        mappings.append(
            {
                "enabled": bool(getattr(m, "enabled", True)),
                "chord": (getattr(m, "chord", "") or "").strip(),
                "label": (getattr(m, "label", "") or "").strip(),
                "group": (getattr(m, "group", "") or "").strip(),
                "operator": (getattr(m, "operator", "") or "").strip(),
                "call_context": (getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT"),
                # Config format (v1): always a real JSON object.
                "kwargs": kwargs_obj,
            }
        )

    return {
        "version": CONFIG_VERSION,
        "timeout_ms": int(getattr(prefs, "timeout_ms", 1200)),
        "overlay": {
            "enabled": bool(getattr(prefs, "overlay_enabled", True)),
            "max_items": int(getattr(prefs, "overlay_max_items", 14)),
            "column_rows": int(getattr(prefs, "overlay_column_rows", 12)),
            "font_size_header": int(getattr(prefs, "overlay_font_size_header", 14)),
            "font_size_chord": int(getattr(prefs, "overlay_font_size_chord", 12)),
            "font_size_body": int(getattr(prefs, "overlay_font_size_body", 12)),
            "color_chord": list(getattr(prefs, "overlay_color_chord", (0.65, 0.8, 1.0, 1.0))),
            "color_label": list(getattr(prefs, "overlay_color_label", (1.0, 1.0, 1.0, 1.0))),
            "color_header": list(getattr(prefs, "overlay_color_header", (1.0, 1.0, 1.0, 1.0))),
            "position": getattr(prefs, "overlay_position", "TOP_LEFT"),
            "offset_x": int(getattr(prefs, "overlay_offset_x", 14)),
            "offset_y": int(getattr(prefs, "overlay_offset_y", 14)),
        },
        "mappings": mappings,
    }


def _enum_items_as_set(prefs, prop_name: str) -> set:
    try:
        p = prefs.bl_rna.properties[prop_name]
        return {item.identifier for item in p.enum_items}
    except Exception:
        return set()


def apply_config(prefs, data: dict) -> list[str]:
    """
    Apply config dict to preferences.
    Returns a list of warnings that the caller may show to the user.
    """
    warnings = []
    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON object")

    version = data.get("version", None)
    if version not in (None, CONFIG_VERSION):
        warnings.append(f"Unsupported config version: {version} (expected {CONFIG_VERSION})")

    # Timeout
    if "timeout_ms" in data:
        try:
            prefs.timeout_ms = int(data["timeout_ms"])
        except Exception:
            warnings.append("Invalid timeout_ms, keeping current")

    # Overlay
    overlay = data.get("overlay", {})
    if isinstance(overlay, dict):
        if "enabled" in overlay:
            prefs.overlay_enabled = bool(overlay["enabled"])
        if "max_items" in overlay:
            try:
                prefs.overlay_max_items = int(overlay["max_items"])
            except Exception:
                warnings.append("Invalid overlay.max_items, keeping current")
        if "column_rows" in overlay:
            try:
                prefs.overlay_column_rows = int(overlay["column_rows"])
            except Exception:
                warnings.append("Invalid overlay.column_rows, keeping current")
        if "font_size_header" in overlay:
            try:
                prefs.overlay_font_size_header = int(overlay["font_size_header"])
            except Exception:
                warnings.append("Invalid overlay.font_size_header, keeping current")
        if "font_size_chord" in overlay:
            try:
                prefs.overlay_font_size_chord = int(overlay["font_size_chord"])
            except Exception:
                warnings.append("Invalid overlay.font_size_chord, keeping current")
        if "font_size_body" in overlay:
            try:
                prefs.overlay_font_size_body = int(overlay["font_size_body"])
            except Exception:
                warnings.append("Invalid overlay.font_size_body, keeping current")

        def _apply_color(attr, key):
            if key not in overlay:
                return
            v = overlay.get(key)
            if isinstance(v, (list, tuple)) and len(v) == 4:
                try:
                    setattr(prefs, attr, tuple(float(x) for x in v))
                except Exception:
                    warnings.append(f"Invalid overlay.{key}, keeping current")
            else:
                warnings.append(f"Invalid overlay.{key}, keeping current")

        _apply_color("overlay_color_chord", "color_chord")
        _apply_color("overlay_color_label", "color_label")
        _apply_color("overlay_color_header", "color_header")

        pos = overlay.get("position", None)
        if isinstance(pos, str):
            valid = _enum_items_as_set(prefs, "overlay_position")
            if pos in valid:
                prefs.overlay_position = pos
            else:
                warnings.append(f'Unknown overlay.position "{pos}", keeping current')

        if "offset_x" in overlay:
            try:
                prefs.overlay_offset_x = int(overlay["offset_x"])
            except Exception:
                warnings.append("Invalid overlay.offset_x, keeping current")
        if "offset_y" in overlay:
            try:
                prefs.overlay_offset_y = int(overlay["offset_y"])
            except Exception:
                warnings.append("Invalid overlay.offset_y, keeping current")

    # Mappings
    mappings = data.get("mappings", None)
    if mappings is None:
        return warnings
    if not isinstance(mappings, list):
        raise ValueError("mappings must be a list")

    prefs.mappings.clear()
    for i, item in enumerate(mappings):
        if not isinstance(item, dict):
            warnings.append(f"Skipping mapping #{i} (not an object)")
            continue
        m = prefs.mappings.add()
        m.enabled = bool(item.get("enabled", True))
        m.chord = (item.get("chord", "") or "").strip()
        m.label = (
            (item.get("label", "") or "").strip()
            or (item.get("operator", "") or "").strip()
            or "(missing label)"
        )
        m.group = (item.get("group", "") or "").strip()
        m.operator = (item.get("operator", "") or "").strip()
        m.call_context = (item.get("call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
        # Config format (v1): require "kwargs" object (no legacy support).
        if "kwargs" in item and not isinstance(item["kwargs"], dict):
            raise ValueError("mappings[].kwargs must be an object")
        m.kwargs_json = json.dumps(item.get("kwargs", {}), ensure_ascii=False)

    return warnings


def loads_json(text: str) -> dict:
    v = json.loads(text)
    if not isinstance(v, dict):
        raise ValueError("Config root must be a JSON object")
    return v


