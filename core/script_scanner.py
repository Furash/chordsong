"""Filesystem scanner for context-scoped custom scripts.

bpy-free by design (layering rule, same as config_io/engine) so all folder
rules are unit-testable without Blender.
"""

from dataclasses import dataclass
from typing import Optional
import json
import os

# Canonical context tokens. Order matters: alias collisions resolve to the
# earliest token in this tuple.
CONTEXT_TOKENS = (
    "view3d", "edit", "object",
    "edit_mesh", "edit_curve", "edit_surface", "edit_text",
    "edit_armature", "edit_metaball", "edit_lattice", "edit_greasepencil",
    "pose", "sculpt", "vertex_paint", "weight_paint", "texture_paint",
    "particle",
    "geonodes", "shader", "image",
)

CHORDSONG_FILE = ".chordsong"

# bpy context.mode -> mode-level token (3D viewport only)
_MODE_TOKENS = {
    "OBJECT": "object",
    "EDIT_MESH": "edit_mesh",
    "EDIT_CURVE": "edit_curve",
    "EDIT_CURVES": "edit_curve",
    "EDIT_SURFACE": "edit_surface",
    "EDIT_TEXT": "edit_text",
    "EDIT_ARMATURE": "edit_armature",
    "EDIT_METABALL": "edit_metaball",
    "EDIT_LATTICE": "edit_lattice",
    "EDIT_GPENCIL": "edit_greasepencil",
    "EDIT_GREASE_PENCIL": "edit_greasepencil",
    "POSE": "pose",
    "SCULPT": "sculpt",
    "SCULPT_CURVES": "sculpt",
    "SCULPT_GPENCIL": "sculpt",
    "SCULPT_GREASE_PENCIL": "sculpt",
    "PAINT_VERTEX": "vertex_paint",
    "PAINT_WEIGHT": "weight_paint",
    "PAINT_TEXTURE": "texture_paint",
    "PARTICLE": "particle",
}


def script_contexts_for(space_type, tree_type=None, mode=None):
    """Token set matching an editor state. Union semantics: a mesh-edit
    viewport matches view3d, edit and edit_mesh folders at once."""
    if space_type == "VIEW_3D":
        tokens = {"view3d"}
        mode_token = _MODE_TOKENS.get(mode or "")
        if mode_token:
            tokens.add(mode_token)
            if mode_token.startswith("edit_"):
                tokens.add("edit")
        return tokens
    if space_type == "NODE_EDITOR":
        return {"geonodes"} if tree_type == "GeometryNodeTree" else {"shader"}
    if space_type == "IMAGE_EDITOR":
        return {"image"}
    return set()
