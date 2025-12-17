"""
Core logic for the addon (no Blender UI drawing).
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

from .config_io import apply_config, dump_prefs, loads_json
from .engine import (
    candidates_for_prefix,
    filter_mappings_by_context,
    find_exact_mapping,
    get_leader_key_token,
    get_leader_key_type,
    get_str_attr,
    normalize_token,
    parse_kwargs,
    set_leader_key_in_keymap,
)

__all__ = [
    "apply_config",
    "candidates_for_prefix",
    "dump_prefs",
    "filter_mappings_by_context",
    "find_exact_mapping",
    "get_leader_key_token",
    "get_leader_key_type",
    "get_str_attr",
    "loads_json",
    "normalize_token",
    "parse_kwargs",
    "set_leader_key_in_keymap",
]