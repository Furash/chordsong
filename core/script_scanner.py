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


@dataclass
class ScriptEntry:
    """One runnable script found in the scripts folder."""
    name: str                    # filename without .py
    path: str                    # absolute path
    context_token: Optional[str]  # None = visible in all contexts
    group: str                   # display group ("" = ungrouped)
    flagged: bool                # True = unrecognized root folder (warn red)


def humanize_folder(name):
    """'_my_tools' -> 'My Tools' (strip leading underscores, _ -> space)."""
    return name.lstrip("_").replace("_", " ").strip().title()


def _load_aliases(root):
    """Default aliases (token -> {token}) merged with .chordsong overrides."""
    aliases = {t: {t} for t in CONTEXT_TOKENS}
    warnings = []
    path = os.path.join(root, CHORDSONG_FILE)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("root must be a JSON object")
            for key, value in data.items():
                if key not in CONTEXT_TOKENS:
                    warnings.append(f"{CHORDSONG_FILE}: unknown context '{key}'")
                    continue
                names = [value] if isinstance(value, str) else value
                if not isinstance(names, list) or not names or \
                        not all(isinstance(n, str) and n.strip() for n in names):
                    warnings.append(f"{CHORDSONG_FILE}: invalid alias for '{key}'")
                    continue
                aliases[key] = {n.strip().lower() for n in names}
        except (OSError, ValueError) as e:
            warnings.append(f"{CHORDSONG_FILE}: {e}")
    return aliases, warnings


def _folder_token_map(aliases, warnings):
    """Reverse aliases to folder-name -> token; earliest token wins collisions."""
    folder_to_token = {}
    for token in CONTEXT_TOKENS:
        for name in sorted(aliases[token]):
            if name in folder_to_token:
                warnings.append(
                    f"alias '{name}' maps to both '{folder_to_token[name]}' "
                    f"and '{token}' — using '{folder_to_token[name]}'"
                )
                continue
            folder_to_token[name] = token
    return folder_to_token


def _list_dir(dirpath, warnings):
    try:
        return sorted(os.listdir(dirpath))
    except OSError as e:
        warnings.append(f"cannot read '{os.path.basename(dirpath)}': {e}")
        return []


def _is_script(dirpath, name):
    return (name.endswith(".py") and not name.startswith("__")
            and os.path.isfile(os.path.join(dirpath, name)))


def _script_entries(dirpath, names, context_token, group, flagged):
    return [
        ScriptEntry(
            name=n[:-3],
            path=os.path.join(dirpath, n),
            context_token=context_token,
            group=group,
            flagged=flagged,
        )
        for n in names if _is_script(dirpath, n)
    ]


def _scan_group_level(dirpath, context_token, warnings):
    """Scripts directly in a context folder, plus one group-folder level."""
    entries = []
    names = _list_dir(dirpath, warnings)
    entries.extend(_script_entries(dirpath, names, context_token, "", False))
    for name in names:
        sub = os.path.join(dirpath, name)
        if not os.path.isdir(sub) or name.startswith("__"):
            continue
        group = humanize_folder(name)
        sub_names = _list_dir(sub, warnings)
        entries.extend(_script_entries(sub, sub_names, context_token, group, False))
        for deep in sub_names:
            if os.path.isdir(os.path.join(sub, deep)) and not deep.startswith("__"):
                warnings.append(f"'{name}/{deep}' is too deep — ignored")
    return entries


def scan_scripts_folder(root):
    """Scan the scripts folder tree.

    Returns (entries, warnings). Never raises for malformed content —
    problems become warnings and, for unrecognized root folders, flagged
    entries that stay visible everywhere.
    """
    entries = []
    warnings = []
    aliases, warnings_a = _load_aliases(root)
    warnings.extend(warnings_a)
    folder_to_token = _folder_token_map(aliases, warnings)

    root_names = _list_dir(root, warnings)
    entries.extend(_script_entries(root, root_names, None, "", False))

    for name in root_names:
        dirpath = os.path.join(root, name)
        if not os.path.isdir(dirpath) or name.startswith("__") or name.startswith("."):
            continue
        if name.startswith("_"):
            # explicit all-contexts group
            group = humanize_folder(name)
            sub_names = _list_dir(dirpath, warnings)
            entries.extend(_script_entries(dirpath, sub_names, None, group, False))
            for deep in sub_names:
                if os.path.isdir(os.path.join(dirpath, deep)) and not deep.startswith("__"):
                    warnings.append(f"'{name}/{deep}' is too deep — ignored")
            continue
        token = folder_to_token.get(name.lower())
        if token is not None:
            entries.extend(_scan_group_level(dirpath, token, warnings))
            continue
        # unrecognized root folder: flag loudly, keep scripts visible
        warnings.append(f"unrecognized folder '{name}'")
        sub_names = _list_dir(dirpath, warnings)
        entries.extend(_script_entries(dirpath, sub_names, None, name, True))

    return entries, warnings


def sort_entries(entries, folders_first=True):
    """Display order: flagged first (always), then grouped-before-ungrouped
    (groups A-Z, names A-Z) when folders_first, else flat name A-Z."""
    if folders_first:
        def key(e):
            return (0 if e.flagged else 1,
                    0 if e.group else 1,
                    e.group.lower(),
                    e.name.lower())
    else:
        def key(e):
            return (0 if e.flagged else 1, e.name.lower())
    return sorted(entries, key=key)
