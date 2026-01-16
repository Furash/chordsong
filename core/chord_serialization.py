"""
Chord serialization for copy/paste sharing.

Provides compact, atomic chord serialization using JSON to enable
easy export/import of chord snippets and reliable round-trip conversion.
"""

import json
from typing import Any

from ..core.engine import get_str_attr

CHORD_SNIPPET_VERSION = 1


def serialize_chords(mappings: list, indices: list[int] = None) -> dict:
    """
    Serialize chord mappings to a compact JSON snippet format.
    
    Args:
        mappings: List of mapping objects to serialize
        indices: Optional list of indices to serialize. If None, serializes all mappings.
    
    Returns:
        Dict with format: {"version": 1, "chords": [...]}
    """
    chords_data = []
    
    # Determine which mappings to serialize
    if indices is not None:
        items_to_serialize = [(i, mappings[i]) for i in indices if 0 <= i < len(mappings)]
    else:
        items_to_serialize = list(enumerate(mappings))
    
    for idx, m in items_to_serialize:
        chord_dict = _serialize_mapping(m)
        if chord_dict:
            chords_data.append(chord_dict)
    
    return {
        "version": CHORD_SNIPPET_VERSION,
        "chords": chords_data
    }


def _serialize_mapping(m) -> dict:
    """Serialize a single mapping to a dict."""
    mapping_type = getattr(m, "mapping_type", "OPERATOR")
    
    # Base properties common to all mappings
    chord_dict = {
        "chord": get_str_attr(m, "chord"),
        "label": get_str_attr(m, "label"),
        "icon": get_str_attr(m, "icon"),
        "group": get_str_attr(m, "group"),
        "context": getattr(m, "context", "VIEW_3D"),
        "mapping_type": mapping_type,
        "enabled": bool(getattr(m, "enabled", True)),
    }
    
    # Add type-specific properties
    if mapping_type == "OPERATOR":
        chord_dict["operator"] = get_str_attr(m, "operator")
        chord_dict["call_context"] = getattr(m, "call_context", "EXEC_DEFAULT")
        
        # Add parameters if present
        kwargs_json = get_str_attr(m, "kwargs_json")
        if kwargs_json and kwargs_json.strip():
            chord_dict["kwargs_json"] = kwargs_json
        
        # Add sub-operators if present
        sub_operators = getattr(m, "sub_operators", [])
        if sub_operators:
            sub_ops_data = []
            for sub_op in sub_operators:
                sub_op_dict = {
                    "operator": get_str_attr(sub_op, "operator"),
                    "call_context": getattr(sub_op, "call_context", "EXEC_DEFAULT"),
                }
                kwargs = get_str_attr(sub_op, "kwargs_json")
                if kwargs and kwargs.strip():
                    sub_op_dict["kwargs_json"] = kwargs
                sub_ops_data.append(sub_op_dict)
            chord_dict["sub_operators"] = sub_ops_data
    
    elif mapping_type == "PYTHON_FILE":
        chord_dict["python_file"] = get_str_attr(m, "python_file")
        
        # Store script parameters
        params = [get_str_attr(m, "kwargs_json")]
        for sp in getattr(m, "script_params", []):
            params.append(get_str_attr(sp, "value"))
        
        # Merge parameters (similar to config_io.py logic)
        from .engine import parse_kwargs
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
        
        if merged_kwargs:
            chord_dict["kwargs"] = merged_kwargs
    
    elif mapping_type == "CONTEXT_PROPERTY":
        chord_dict["context_path"] = get_str_attr(m, "context_path")
        chord_dict["property_value"] = get_str_attr(m, "property_value")
        
        # Add sub-items if present
        sub_items = getattr(m, "sub_items", [])
        if sub_items:
            sub_items_data = []
            for sub_item in sub_items:
                sub_item_dict = {
                    "path": get_str_attr(sub_item, "path"),
                    "value": get_str_attr(sub_item, "value"),
                }
                sub_items_data.append(sub_item_dict)
            chord_dict["sub_items"] = sub_items_data
    
    elif mapping_type == "CONTEXT_TOGGLE":
        chord_dict["context_path"] = get_str_attr(m, "context_path")
        chord_dict["sync_toggles"] = bool(getattr(m, "sync_toggles", False))
        
        # Add sub-items if present
        sub_items = getattr(m, "sub_items", [])
        if sub_items:
            sub_items_data = []
            for sub_item in sub_items:
                sub_item_dict = {
                    "path": get_str_attr(sub_item, "path"),
                }
                sub_items_data.append(sub_item_dict)
            chord_dict["sub_items"] = sub_items_data
    
    return chord_dict


def deserialize_chords(data: dict | str) -> tuple[list[dict], list[str]]:
    """
    Deserialize chord snippets from JSON.
    
    Args:
        data: Either a dict or JSON string with format {"version": 1, "chords": [...]}
    
    Returns:
        Tuple of (chord_dicts, warnings) where chord_dicts is a list of dicts
        ready to be added to mappings, and warnings is a list of warning messages.
    """
    warnings = []
    
    # Parse JSON if needed
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    if not isinstance(data, dict):
        raise ValueError("Chord snippet must be a JSON object")
    
    # Validate version
    version = data.get("version", None)
    if version != CHORD_SNIPPET_VERSION:
        warnings.append(f"Unsupported snippet version: {version} (current: {CHORD_SNIPPET_VERSION})")
    
    # Extract chords array
    chords = data.get("chords", [])
    if not isinstance(chords, list):
        raise ValueError("'chords' field must be an array")
    
    # Validate each chord has minimum required fields
    chord_dicts = []
    for i, chord in enumerate(chords):
        if not isinstance(chord, dict):
            warnings.append(f"Chord {i} is not an object, skipping")
            continue
        
        # Validate required fields
        if not chord.get("chord"):
            warnings.append(f"Chord {i} missing 'chord' field, skipping")
            continue
        
        if not chord.get("mapping_type"):
            warnings.append(f"Chord {i} missing 'mapping_type' field, using OPERATOR")
            chord["mapping_type"] = "OPERATOR"
        
        # Validate mapping type
        valid_types = {"OPERATOR", "PYTHON_FILE", "CONTEXT_PROPERTY", "CONTEXT_TOGGLE"}
        if chord["mapping_type"] not in valid_types:
            warnings.append(f"Chord {i} has invalid mapping_type: {chord['mapping_type']}, skipping")
            continue
        
        chord_dicts.append(chord)
    
    return chord_dicts, warnings


def serialize_to_json_string(mappings: list, indices: list[int] = None, indent: int = 2) -> str:
    """
    Serialize chord mappings to a JSON string.
    
    Args:
        mappings: List of mapping objects to serialize
        indices: Optional list of indices to serialize
        indent: JSON indentation level (default: 2)
    
    Returns:
        JSON string
    """
    data = serialize_chords(mappings, indices)
    return json.dumps(data, indent=indent, ensure_ascii=False)


def deserialize_from_json_string(json_str: str) -> tuple[list[dict], list[str]]:
    """
    Deserialize chord snippets from a JSON string.
    
    Args:
        json_str: JSON string with format {"version": 1, "chords": [...]}
    
    Returns:
        Tuple of (chord_dicts, warnings)
    """
    return deserialize_chords(json_str)
