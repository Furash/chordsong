"""Overlay rendering for chord capture display."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

# Expose API
from .cache import clear_overlay_cache, get_prefs_hash
from .render import draw_overlay, draw_fading_overlay

__all__ = [
    "clear_overlay_cache",
    "get_prefs_hash",
    "draw_overlay",
    "draw_fading_overlay",
]
