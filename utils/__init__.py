"""Utility modules for Chord Song.

No package-level re-exports — callers import from submodules directly
(`from ..utils.render import capture_viewport_context`). Keeping this module
empty lets bpy-free submodules (context_path, fuzzy, addon_package) be
imported in unit tests without pulling bpy via render.py.
"""
