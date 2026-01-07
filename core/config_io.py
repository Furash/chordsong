import json

# pylint: disable=broad-exception-caught

import bpy  # type: ignore
from .engine import parse_kwargs, get_str_attr, get_leader_key_type, set_leader_key_in_keymap

CHORDSONG_CONFIG_VERSION = 1

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
            # Store parameters as dict (kwargs) - preserve row structure with underscore prefix
            # Parse each row separately to track which parameters start new rows
            params = [get_str_attr(m, "kwargs_json")]
            for sp in getattr(m, "script_params", []):
                params.append(sp.value)
            
            # Merge all kwargs, marking the first key in each new row with underscore prefix
            merged_kwargs = {}
            for row_idx, param_str in enumerate(params):
                if not param_str.strip():
                    continue
                row_kwargs = parse_kwargs(param_str)
                is_first_key_in_row = True
                for key, value in row_kwargs.items():
                    # If this is a new row (row_idx > 0) and it's the first key in that row, prefix with underscore
                    if row_idx > 0 and is_first_key_in_row:
                        merged_kwargs[f"_{key}"] = value
                        is_first_key_in_row = False
                    else:
                        # Same row as previous, or first row
                        merged_kwargs[key] = value
                        is_first_key_in_row = False
            
            mapping_dict["kwargs"] = merged_kwargs
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
        "version": CHORDSONG_CONFIG_VERSION,
        "scripts_folder": get_str_attr(prefs, "scripts_folder"),
        "allow_custom_user_scripts": bool(getattr(prefs, "allow_custom_user_scripts", False)),
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


def dump_prefs_filtered(prefs, filter_options: dict) -> dict:
    """
    Serialize addon preferences to a JSON-serializable dict with filtering.
    
    Args:
        prefs: Addon preferences object
        filter_options: Dict with keys:
            - mappings: bool - include mappings
            - groups: bool - include group definitions
            - overlay: bool - include overlay settings
            - scripts_folder: bool - include scripts folder
            - leader_key: bool - include leader key
            - selected_group_names: set[str] - set of group names to include in mappings
    """
    result = {}
    
    # Always include version
    result["version"] = CHORDSONG_CONFIG_VERSION
    
    # Scripts folder
    if filter_options.get("scripts_folder", True):
        result["scripts_folder"] = get_str_attr(prefs, "scripts_folder")
        result["allow_custom_user_scripts"] = bool(getattr(prefs, "allow_custom_user_scripts", False))
    
    # Leader key
    if filter_options.get("leader_key", True):
        result["leader_key"] = get_leader_key_type()
    
    # Overlay settings
    if filter_options.get("overlay", True):
        result["overlay"] = {
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
        }
    
    # Groups
    selected_group_names = filter_options.get("selected_group_names", None)
    if filter_options.get("groups", True):
        groups = []
        for grp in getattr(prefs, "groups", []):
            group_name = (getattr(grp, "name", "") or "").strip()
            # If filtering by groups, only include selected ones
            if selected_group_names is None or group_name in selected_group_names:
                groups.append({
                    "name": group_name,
                    "display_order": int(getattr(grp, "display_order", 0)),
                    "expanded": bool(getattr(grp, "expanded", False)),
                })
        if groups:
            result["groups"] = groups
    
    # Mappings
    if filter_options.get("mappings", True):
        mappings = []
        for m in getattr(prefs, "mappings", []):
            # Filter by group if group filtering is enabled
            if selected_group_names is not None:
                mapping_group = (get_str_attr(m, "group") or "").strip()
                # Include if mapping belongs to a selected group, or if it's ungrouped and we want ungrouped
                if mapping_group and mapping_group not in selected_group_names:
                    continue
            
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
                params = [get_str_attr(m, "kwargs_json")]
                for sp in getattr(m, "script_params", []):
                    params.append(sp.value)
                
                merged_kwargs = {}
                for row_idx, param_str in enumerate(params):
                    if not param_str.strip():
                        continue
                    row_kwargs = parse_kwargs(param_str)
                    is_first_key_in_row = True
                    for key, value in row_kwargs.items():
                        if row_idx > 0 and is_first_key_in_row:
                            merged_kwargs[f"_{key}"] = value
                            is_first_key_in_row = False
                        else:
                            merged_kwargs[key] = value
                            is_first_key_in_row = False
                
                mapping_dict["kwargs"] = merged_kwargs
            elif mapping_type == "CONTEXT_TOGGLE":
                mapping_dict["sync_toggles"] = bool(getattr(m, "sync_toggles", False))
                mapping_dict["context_path"] = get_str_attr(m, "context_path")
            elif mapping_type == "CONTEXT_PROPERTY":
                mapping_dict["context_path"] = get_str_attr(m, "context_path")
                mapping_dict["property_value"] = get_str_attr(m, "property_value")
            else:
                operators_list = []
                
                primary_op = get_str_attr(m, "operator")
                if primary_op:
                    operators_list.append({
                        "operator": primary_op,
                        "call_context": getattr(m, "call_context", "EXEC_DEFAULT") or "EXEC_DEFAULT",
                        "kwargs": parse_kwargs(get_str_attr(m, "kwargs_json")),
                    })
                
                for sub in getattr(m, "sub_operators", []):
                    if sub.operator.strip():
                        operators_list.append({
                            "operator": sub.operator.strip(),
                            "call_context": sub.call_context,
                            "kwargs": parse_kwargs(sub.kwargs_json),
                        })
                
                mapping_dict["operators"] = operators_list

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
        
        if mappings:
            result["mappings"] = mappings
    
    return result

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
    if config_version not in (None, 1):
        warnings.append(f"Unsupported config version: {config_version} (current {CHORDSONG_CONFIG_VERSION})")

    # Scripts folder
    if "scripts_folder" in data:
        scripts_folder = data.get("scripts_folder", "")
        if isinstance(scripts_folder, str):
            prefs.scripts_folder = scripts_folder.strip()
    
    # Allow custom user scripts - default to False for security
    # Only enable if explicitly set to True in config
    if "allow_custom_user_scripts" in data:
        allow_scripts = data.get("allow_custom_user_scripts", False)
        if isinstance(allow_scripts, bool):
            prefs.allow_custom_user_scripts = allow_scripts
    else:
        # Explicitly set to False if not in config (for backward compatibility and security)
        prefs.allow_custom_user_scripts = False

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
    for item in mappings:
        if isinstance(item, dict):
            _add_mapping_from_dict(prefs, item)

    return warnings

def _add_mapping_from_dict(prefs, item: dict):
    """Helper function to add a single mapping from a dict to prefs.mappings."""
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
        # Restore parameters: prefer kwargs (dict), fall back to params (list) for backward compatibility
        kwargs_dict = item.get("kwargs", {})
        params = item.get("params", [])
        
        if kwargs_dict:
            # Use kwargs dict (preferred format)
            # Reconstruct rows based on underscore-prefixed keys
            current_row = {}
            rows = []
            
            for key, value in kwargs_dict.items():
                if key.startswith("_"):
                    # This key starts a new row - save previous row and start new one
                    if current_row:
                        rows.append(current_row)
                    current_row = {key[1:]: value}  # Remove underscore prefix
                else:
                    # Same row as previous
                    current_row[key] = value
            
            # Don't forget the last row
            if current_row:
                rows.append(current_row)
            
            # Convert rows back to string format
            if rows:
                m.kwargs_json = _kwargs_dict_to_str(rows[0])
                m.script_params.clear()
                for row in rows[1:]:
                    sp = m.script_params.add()
                    sp.value = _kwargs_dict_to_str(row)
            else:
                m.kwargs_json = ""
                m.script_params.clear()
        elif isinstance(params, list) and params:
            # Fall back to params list (for backward compatibility)
            m.kwargs_json = params[0]
            m.script_params.clear()
            for p_val in params[1:]:
                sp = m.script_params.add()
                sp.value = p_val
        else:
            m.kwargs_json = ""
            m.script_params.clear()
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

def apply_config_append(prefs, data: dict) -> list[str]:
    """
    Append/merge config dict to existing preferences (doesn't clear existing data).
    Returns a list of warnings that the caller may show to the user.
    """
    warnings = []
    if not isinstance(data, dict):
        raise ValueError("Config root must be a JSON object")

    config_version = data.get("version", None)
    if config_version not in (None, 1):
        warnings.append(f"Unsupported config version: {config_version} (current {CHORDSONG_CONFIG_VERSION})")

    # Note: We don't merge scripts_folder, leader_key, or overlay settings
    # to preserve the user's current configuration

    # Merge groups: add if name doesn't exist, otherwise skip (keep existing)
    groups_data = data.get("groups", None)
    if isinstance(groups_data, list):
        existing_group_names = {get_str_attr(grp, "name") for grp in prefs.groups}
        for grp_item in groups_data:
            if isinstance(grp_item, dict):
                grp_name = (grp_item.get("name", "") or "").strip()
                if grp_name and grp_name not in existing_group_names:
                    grp = prefs.groups.add()
                    grp.name = grp_name
                    grp.display_order = int(grp_item.get("display_order", 0))
                    grp.expanded = bool(grp_item.get("expanded", False))

    # Append mappings: add all new mappings without clearing existing ones
    mappings = data.get("mappings", None)
    if isinstance(mappings, list):
        for item in mappings:
            if isinstance(item, dict):
                _add_mapping_from_dict(prefs, item)

    return warnings

def loads_json(text: str) -> dict:
    v = json.loads(text)
    if not isinstance(v, dict):
        raise ValueError("Config root must be a JSON object")
    return v
