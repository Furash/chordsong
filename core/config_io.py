import json

# pylint: disable=broad-exception-caught

import bpy  # type: ignore
from .engine import parse_kwargs, get_str_attr, get_leader_key_type, set_leader_key_in_keymap

CONFIG_VERSION = 1

def dump_prefs(prefs) -> dict:
    """Serialize addon preferences to a JSON-serializable dict."""
    mappings = []
    for m in getattr(prefs, "mappings", []):
        kwargs_json = get_str_attr(m, "kwargs_json")
        # Parse Python-like syntax to dict for JSON serialization
        kwargs_obj = parse_kwargs(kwargs_json)

        mapping_type = getattr(m, "mapping_type", "OPERATOR")
        mapping_dict = {
            "enabled": bool(getattr(m, "enabled", True)),
            "chord": get_str_attr(m, "chord"),
            "label": get_str_attr(m, "label"),
            "icon": get_str_attr(m, "icon"),
            "group": get_str_attr(m, "group"),
            "context": getattr(m, "context", "VIEW_3D"),
            "mapping_type": mapping_type,
        }

        if mapping_type == "PYTHON_FILE":
            mapping_dict["python_file"] = get_str_attr(m, "python_file")
        elif mapping_type == "CONTEXT_TOGGLE":
            mapping_dict["context_path"] = get_str_attr(m, "context_path")
        else:
            mapping_dict["operator"] = get_str_attr(m, "operator")
            mapping_dict["call_context"] = getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT"
            # Config format (v1): always a real JSON object.
            mapping_dict["kwargs"] = kwargs_obj

        mappings.append(mapping_dict)

    # Serialize groups
    groups = []
    for grp in getattr(prefs, "groups", []):
        groups.append({
            "name": (getattr(grp, "name", "") or "").strip(),
            "display_order": int(getattr(grp, "display_order", 0)),
        })

    return {
        "version": CONFIG_VERSION,
        "scripts_folder": get_str_attr(prefs, "scripts_folder"),
        "leader_key": get_leader_key_type(),
        "overlay": {
            "enabled": bool(getattr(prefs, "overlay_enabled", True)),
            "fading_enabled": bool(getattr(prefs, "overlay_fading_enabled", True)),
            "show_header": bool(getattr(prefs, "overlay_show_header", True)),
            "show_footer": bool(getattr(prefs, "overlay_show_footer", True)),
            "max_items": int(getattr(prefs, "overlay_max_items", 14)),
            "column_rows": int(getattr(prefs, "overlay_column_rows", 12)),
            "font_size_header": int(getattr(prefs, "overlay_font_size_header", 14)),
            "font_size_chord": int(getattr(prefs, "overlay_font_size_chord", 12)),
            "font_size_body": int(getattr(prefs, "overlay_font_size_body", 12)),
            "font_size_footer": int(getattr(prefs, "overlay_font_size_footer", 12)),
            "font_size_fading": int(getattr(prefs, "overlay_font_size_fading", 24)),
            "color_chord": list(getattr(prefs, "overlay_color_chord", (0.65, 0.8, 1.0, 1.0))),
            "color_label": list(getattr(prefs, "overlay_color_label", (1.0, 1.0, 1.0, 1.0))),
            "color_header": list(getattr(prefs, "overlay_color_header", (1.0, 1.0, 1.0, 1.0))),
            "color_icon": list(getattr(prefs, "overlay_color_icon", (0.8, 0.8, 0.8, 0.7))),
            "color_recents_hotkey": list(getattr(prefs, "overlay_color_recents_hotkey", (0.65, 0.8, 1.0, 1.0))),
            "color_list_background": list(getattr(prefs, "overlay_list_background", (0.0, 0.0, 0.0, 0.35))),
            "color_header_background": list(getattr(prefs, "overlay_header_background", (0.0, 0.0, 0.0, 0.35))),
            "color_footer_background": list(getattr(prefs, "overlay_footer_background", (0.0, 0.0, 0.0, 0.35))),
            "gap": int(getattr(prefs, "overlay_gap", 10)),
            "column_gap": int(getattr(prefs, "overlay_column_gap", 30)),
            "line_height": float(getattr(prefs, "overlay_line_height", 1.5)),
            "footer_gap": int(getattr(prefs, "overlay_footer_gap", 20)),
            "footer_token_gap": int(getattr(prefs, "overlay_footer_token_gap", 10)),
            "footer_label_gap": int(getattr(prefs, "overlay_footer_label_gap", 10)),
            "position": getattr(prefs, "overlay_position", "TOP_LEFT"),
            "style": getattr(prefs, "overlay_folder_style", "GROUPS_FIRST"),
            "offset_x": int(getattr(prefs, "overlay_offset_x", 14)),
            "offset_y": int(getattr(prefs, "overlay_offset_y", 14)),
        },
        "groups": groups,
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

    # Scripts folder
    if "scripts_folder" in data:
        scripts_folder = data.get("scripts_folder", "")
        if isinstance(scripts_folder, str):
            prefs.scripts_folder = scripts_folder.strip()

    # Leader key
    if "leader_key" in data:
        leader_key = data.get("leader_key", "SPACE")
        if isinstance(leader_key, str):
            # Validate it's a reasonable key type
            # Common key types that make sense for a leader key
            valid_keys = {
                "SPACE", "ACCENT_GRAVE", "QUOTE", "COMMA", "SEMI_COLON",
                "PERIOD", "SLASH", "BACK_SLASH", "EQUAL", "MINUS",
                "LEFT_BRACKET", "RIGHT_BRACKET"
            }
            if leader_key in valid_keys:
                set_leader_key_in_keymap(leader_key)
            else:
                warnings.append(f'Unknown leader_key "{leader_key}", keeping current')

    # Overlay
    overlay = data.get("overlay", {})
    if isinstance(overlay, dict):
        # Boolean properties
        bool_props = {
            "enabled": "overlay_enabled",
            "fading_enabled": "overlay_fading_enabled",
            "show_header": "overlay_show_header",
            "show_footer": "overlay_show_footer",
        }
        for key, attr in bool_props.items():
            if key in overlay:
                setattr(prefs, attr, bool(overlay[key]))

        # Integer properties - use a loop to reduce duplication
        int_props = {
            "max_items": "overlay_max_items",
            "column_rows": "overlay_column_rows",
            "font_size_header": "overlay_font_size_header",
            "font_size_chord": "overlay_font_size_chord",
            "font_size_body": "overlay_font_size_body",
            "font_size_footer": "overlay_font_size_footer",
            "font_size_fading": "overlay_font_size_fading",
            "gap": "overlay_gap",
            "column_gap": "overlay_column_gap",
            "footer_gap": "overlay_footer_gap",
            "footer_token_gap": "overlay_footer_token_gap",
            "footer_label_gap": "overlay_footer_label_gap",
            "offset_x": "overlay_offset_x",
            "offset_y": "overlay_offset_y",
        }

        # Float properties
        float_props = {
            "line_height": "overlay_line_height",
        }

        for key, attr in float_props.items():
            if key in overlay:
                try:
                    setattr(prefs, attr, float(overlay[key]))
                except Exception:
                    warnings.append(f"Invalid overlay.{key}, keeping current")

        for key, attr in int_props.items():
            if key in overlay:
                try:
                    setattr(prefs, attr, int(overlay[key]))
                except Exception:
                    warnings.append(f"Invalid overlay.{key}, keeping current")

        # Color properties - use a loop
        color_props = {
            "color_chord": "overlay_color_chord",
            "color_label": "overlay_color_label",
            "color_header": "overlay_color_header",
            "color_icon": "overlay_color_icon",
            "color_recents_hotkey": "overlay_color_recents_hotkey",
            "color_list_background": "overlay_list_background",
            "color_header_background": "overlay_header_background",
            "color_footer_background": "overlay_footer_background",
        }

        for key, attr in color_props.items():
            if key in overlay:
                v = overlay[key]
                if isinstance(v, (list, tuple)) and len(v) == 4:
                    try:
                        setattr(prefs, attr, tuple(float(x) for x in v))
                    except Exception:
                        warnings.append(f"Invalid overlay.{key}, keeping current")
                else:
                    warnings.append(f"Invalid overlay.{key}, keeping current")

        # Position enum
        pos = overlay.get("position", None)
        if isinstance(pos, str):
            valid = _enum_items_as_set(prefs, "overlay_position")
            if pos in valid:
                prefs.overlay_position = pos
            else:
                warnings.append(f'Unknown overlay.position "{pos}", keeping current')

        # Folder/Overlay style enum
        style = overlay.get("style", None)
        if isinstance(style, str):
            valid = _enum_items_as_set(prefs, "overlay_folder_style")
            if style in valid:
                prefs.overlay_folder_style = style
            else:
                warnings.append(f'Unknown overlay.style "{style}", keeping current')

    # Groups - Load groups before mappings for proper validation
    groups_data = data.get("groups", None)
    if groups_data is not None:
        if not isinstance(groups_data, list):
            warnings.append("groups must be a list, skipping")
        else:
            prefs.groups.clear()
            for i, grp_item in enumerate(groups_data):
                if not isinstance(grp_item, dict):
                    warnings.append(f"Skipping group #{i} (not an object)")
                    continue
                grp = prefs.groups.add()
                grp.name = (grp_item.get("name", "") or "").strip()
                grp.display_order = int(grp_item.get("display_order", 0))

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
        m.icon = (item.get("icon", "") or "").strip()
        m.group = (item.get("group", "") or "").strip()
        m.context = item.get("context", "VIEW_3D")

        # Handle mapping type (default to OPERATOR for backward compatibility)
        mapping_type = item.get("mapping_type", "OPERATOR")
        m.mapping_type = mapping_type

        if mapping_type == "PYTHON_FILE":
            m.python_file = (item.get("python_file", "") or "").strip()
            m.label = (
                (item.get("label", "") or "").strip()
                or m.python_file
                or "(missing label)"
            )
        elif mapping_type == "CONTEXT_TOGGLE":
            m.context_path = (item.get("context_path", "") or "").strip()
            m.label = (
                (item.get("label", "") or "").strip()
                or m.context_path
                or "(missing label)"
            )
        else:
            m.operator = (item.get("operator", "") or "").strip()
            # Use call_context from JSON if specified, otherwise default to EXEC_DEFAULT
            m.call_context = (item.get("call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
            m.label = (
                (item.get("label", "") or "").strip()
                or m.operator
                or "(missing label)"
            )
            # Config format (v1): require "kwargs" object (no legacy support).
            if "kwargs" in item and not isinstance(item["kwargs"], dict):
                raise ValueError("mappings[].kwargs must be an object")
            kwargs_dict = item.get("kwargs", {})
            # Convert dict to Python-like syntax: key = value, key2 = value2
            if kwargs_dict:
                parts = []
                for key, value in kwargs_dict.items():
                    if isinstance(value, str):
                        parts.append(f'{key} = "{value}"')
                    elif isinstance(value, bool):
                        parts.append(f"{key} = {str(value)}")
                    elif value is None:
                        parts.append(f"{key} = None")
                    else:
                        parts.append(f"{key} = {value}")
                m.kwargs_json = ", ".join(parts)
            else:
                m.kwargs_json = ""

    # Backward compatibility: if no groups were in config, extract from mappings
    if groups_data is None:
        unique_groups = set()
        for m in prefs.mappings:
            group_name = (getattr(m, "group", "") or "").strip()
            if group_name:
                unique_groups.add(group_name)

        for group_name in sorted(unique_groups):
            grp = prefs.groups.add()
            grp.name = group_name

    return warnings

def loads_json(text: str) -> dict:
    v = json.loads(text)
    if not isinstance(v, dict):
        raise ValueError("Config root must be a JSON object")
    return v
