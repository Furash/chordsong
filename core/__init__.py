"""
Core logic for the addon (no Blender UI drawing).
"""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

from .config_io import apply_config, dump_prefs, loads_json
from .engine import candidates_for_prefix, find_exact_mapping, normalize_token, parse_kwargs

__all__ = [
    "apply_config",
    "dump_prefs",
    "loads_json",
    "candidates_for_prefix",
    "find_exact_mapping",
    "normalize_token",
    "parse_kwargs",
]