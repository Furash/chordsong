import json

# pylint: disable=broad-exception-caught

import bpy  # type: ignore
from .engine import parse_kwargs, get_str_attr, get_leader_key_type, set_leader_key_in_keymap

CONFIG_VERSION = 2

def _ensure_json_serializable(obj):
    """Recursively convert sets to lists to ensure JSON serializability."""
    if isinstance(obj, dict):
        return {k: _ensure_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_ensure_json_serializable(i) for i in obj]
    elif isinstance(obj, set):
        return [_ensure_json_serializable(i) for i in list(obj)]
    return obj

def dump_prefs(prefs) -> dict:
    """Serialize addon preferences to a JSON-serializable dict."""
    mappings = []
    for m in getattr(prefs, "mappings", []):
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
            # Store parameters as a list of strings to preserve UI rows
            params = [get_str_attr(m, "kwargs_json")]
            for sp in getattr(m, "script_params", []):
                params.append(sp.value)
            mapping_dict["params"] = params
            
            # Also keep 'kwargs' for compatibility/readability
            all_str = ", ".join([p for p in params if p.strip()])
            mapping_dict["kwargs"] = parse_kwargs(all_str)
        elif mapping_type == "CONTEXT_TOGGLE":
            mapping_dict["sync_toggles"] = bool(getattr(m, "sync_toggles", False))
            mapping_dict["context_path"] = get_str_attr(m, "context_path")
        elif mapping_type == "CONTEXT_PROPERTY":
            mapping_dict["context_path"] = get_str_attr(m, "context_path")
            mapping_dict["property_value"] = get_str_attr(m, "property_value")
        else:
            # Consolidate all operators into a single list
            operators_list = []
            
            # 1. Primary operator
            primary_op = get_str_attr(m, "operator")
            if primary_op:
                operators_list.append({
                    "operator": primary_op,
                    "call_context": getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT",
                    "kwargs": parse_kwargs(get_str_attr(m, "kwargs_json")),
                })
            
            # 2. Sub-operators
            for sub in getattr(m, "sub_operators", []):
                if sub.operator.strip():
                    operators_list.append({
                        "operator": sub.operator.strip(),
                        "call_context": sub.call_context,
                        "kwargs": parse_kwargs(sub.kwargs_json),
                    })
            
            mapping_dict["operators"] = operators_list

        # Serialize sub_items (for toggles/properties)
        sub_items_list = []
        for sub in getattr(m, "sub_items", []):
            if sub.path.strip():
                sub_items_list.append({
                    "path": sub.path.strip(),
                    "value": sub.value.strip(),
                })
        if sub_items_list:
            mapping_dict["sub_items"] = sub_items_list

        mappings.append(_ensure_json_serializable(mapping_dict))

    # Serialize groups
    groups = []
    for grp in getattr(prefs, "groups", []):
        groups.append({
            "name": (getattr(grp, "name", "") or "").strip(),
            "display_order": int(getattr(grp, "display_order", 0)),
            "expanded": bool(getattr(grp, "expanded", False)),
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
            "font_size_toggle": int(getattr(prefs, "overlay_font_size_toggle", 12)),
            "toggle_offset_y": int(getattr(prefs, "overlay_toggle_offset_y", 0)),
            "color_chord": list(getattr(prefs, "overlay_color_chord", (0.65, 0.8, 1.0, 1.0))),
            "color_label": list(getattr(prefs, "overlay_color_label", (1.0, 1.0, 1.0, 1.0))),
            "color_header": list(getattr(prefs, "overlay_color_header", (1.0, 1.0, 1.0, 1.0))),
            "color_icon": list(getattr(prefs, "overlay_color_icon", (0.8, 0.8, 0.8, 0.7))),
            "color_toggle_on": list(getattr(prefs, "overlay_color_toggle_on", (0.65, 0.8, 1.0, 0.4))),
            "color_toggle_off": list(getattr(prefs, "overlay_color_toggle_off", (1.0, 1.0, 1.0, 0.2))),
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
            "ungrouped_expanded": bool(getattr(prefs, "ungrouped_expanded", False)),
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

def _kwargs_dict_to_str(kwargs_dict: dict) -> str:
    """Convert dict to Python-like syntax: key = value, key2 = value2"""
    if not kwargs_dict:
        return ""
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
    return ", ".join(parts)

def apply_config(prefs, data: dict) -> list[str]:
    """
    Apply config dict to preferences.
    Returns a list of warnings that the caller may show to the user.
    """
    warnings = []
    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON object")

    config_version = data.get("version", None)
    if config_version not in (None, 1, 2):
        warnings.append(f"Unsupported config version: {config_version} (current {CONFIG_VERSION})")

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
            valid_keys = {
                "SPACE", "ACCENT_GRAVE", "QUOTE", "COMMA", "SEMI_COLON",
                "PERIOD", "SLASH", "BACK_SLASH", "EQUAL", "MINUS",
                "LEFT_BRACKET", "RIGHT_BRACKET"
            }
            if leader_key in valid_keys:
                set_leader_key_in_keymap(leader_key)
            else:
                warnings.append(f'Unknown leader_key "{leader_key}", keeping current')

    overlay = data.get("overlay", {})
    if isinstance(overlay, dict):
        bool_props = {
            "enabled": "overlay_enabled",
            "fading_enabled": "overlay_fading_enabled",
            "show_header": "overlay_show_header",
            "show_footer": "overlay_show_footer",
        }
        for key, attr in bool_props.items():
            if key in overlay:
                setattr(prefs, attr, bool(overlay[key]))
        
        if "ungrouped_expanded" in overlay:
            prefs.ungrouped_expanded = bool(overlay["ungrouped_expanded"])

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
            "font_size_toggle": "overlay_font_size_toggle",
            "toggle_offset_y": "overlay_toggle_offset_y",
        }
        for key, attr in int_props.items():
            if key in overlay:
                try: setattr(prefs, attr, int(overlay[key]))
                except: pass

        float_props = {"line_height": "overlay_line_height"}
        for key, attr in float_props.items():
            if key in overlay:
                try: setattr(prefs, attr, float(overlay[key]))
                except: pass

        color_props = {
            "color_chord": "overlay_color_chord", "color_label": "overlay_color_label",
            "color_header": "overlay_color_header", "color_icon": "overlay_color_icon",
            "color_toggle_on": "overlay_color_toggle_on", "color_toggle_off": "overlay_color_toggle_off",
            "color_recents_hotkey": "overlay_color_recents_hotkey",
            "color_list_background": "overlay_list_background",
            "color_header_background": "overlay_header_background",
            "color_footer_background": "overlay_footer_background",
        }
        for key, attr in color_props.items():
            if key in overlay:
                v = overlay[key]
                if isinstance(v, (list, tuple)) and len(v) == 4:
                    setattr(prefs, attr, tuple(float(x) for x in v))

        pos = overlay.get("position", "TOP_LEFT")
        if pos in _enum_items_as_set(prefs, "overlay_position"):
            prefs.overlay_position = pos

        style = overlay.get("style", "GROUPS_FIRST")
        if style in _enum_items_as_set(prefs, "overlay_folder_style"):
            prefs.overlay_folder_style = style

    groups_data = data.get("groups", None)
    if isinstance(groups_data, list):
        prefs.groups.clear()
        for grp_item in groups_data:
            if isinstance(grp_item, dict):
                grp = prefs.groups.add()
                grp.name = (grp_item.get("name", "") or "").strip()
                grp.display_order = int(grp_item.get("display_order", 0))
                grp.expanded = bool(grp_item.get("expanded", False))

    mappings = data.get("mappings", None)
    if not isinstance(mappings, list):
        return warnings

    prefs.mappings.clear()
    for i, item in enumerate(mappings):
        if not isinstance(item, dict): continue
        m = prefs.mappings.add()
        m.enabled = bool(item.get("enabled", True))
        m.chord = (item.get("chord", "") or "").strip()
        m.icon = (item.get("icon", "") or "").strip()
        m.group = (item.get("group", "") or "").strip()
        m.context = item.get("context", "VIEW_3D")
        m.mapping_type = item.get("mapping_type", "OPERATOR")
        m.sync_toggles = bool(item.get("sync_toggles", False))
        m.label = (item.get("label", "") or "").strip()

        if m.mapping_type == "PYTHON_FILE":
            m.python_file = (item.get("python_file", "") or "").strip()
            # Restore parameters from list or dictionary
            params = item.get("params", [])
            if isinstance(params, list) and params:
                m.kwargs_json = params[0]
                m.script_params.clear()
                for p_val in params[1:]:
                    sp = m.script_params.add()
                    sp.value = p_val
            else:
                # Fallback to old format
                m.kwargs_json = _kwargs_dict_to_str(item.get("kwargs", {}))
        elif m.mapping_type == "CONTEXT_TOGGLE":
            m.context_path = (item.get("context_path", "") or "").strip()
        elif m.mapping_type == "CONTEXT_PROPERTY":
            m.context_path = (item.get("context_path", "") or "").strip()
            m.property_value = (item.get("property_value", "") or "").strip()
        else:
            # Check for version 2 format (consolidated list)
            operators = item.get("operators", [])
            if isinstance(operators, list) and operators:
                for idx, op_data in enumerate(operators):
                    if not isinstance(op_data, dict): continue
                    op_id = (op_data.get("operator", "") or "").strip()
                    op_ctx = (op_data.get("call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
                    op_kwargs = _kwargs_dict_to_str(op_data.get("kwargs", {}))
                    if idx == 0:
                        m.operator = op_id
                        m.call_context = op_ctx
                        m.kwargs_json = op_kwargs
                    else:
                        sub = m.sub_operators.add()
                        sub.operator = op_id
                        sub.call_context = op_ctx
                        sub.kwargs_json = op_kwargs
            else:
                # Backward compatibility (Version 1)
                m.operator = (item.get("operator", "") or "").strip()
                m.call_context = (item.get("call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
                m.kwargs_json = _kwargs_dict_to_str(item.get("kwargs", {}))
                for sub_data in item.get("sub_operators", []):
                    if isinstance(sub_data, dict):
                        sub = m.sub_operators.add()
                        sub.operator = (sub_data.get("operator", "") or "").strip()
                        sub.call_context = (sub_data.get("call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT").strip()
                        sub.kwargs_json = _kwargs_dict_to_str(sub_data.get("kwargs", {}))

        for sub_data in item.get("sub_items", []):
            if isinstance(sub_data, dict):
                sub = m.sub_items.add()
                sub.path = (sub_data.get("path", "") or "").strip()
                sub.value = (sub_data.get("value", "") or "").strip()

    return warnings

def loads_json(text: str) -> dict:
    v = json.loads(text)
    if not isinstance(v, dict):
        raise ValueError("Config root must be a JSON object")
    return v
