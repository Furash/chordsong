"""Filesystem scanner for context-scoped custom scripts.

bpy-free by design (layering rule, same as config_io/engine) so all folder
rules are unit-testable without Blender.
"""

from dataclasses import dataclass
from typing import Optional
import json
import os

# Context tokens are organized in strict nesting levels:
#   1. editor:      view3d, geonodes, shader, image
#   2. object type: mesh, curve, ... (active object's type)
#   3. mode:        object, edit, sculpt, ...
# Folders nest editor > type > mode; levels may be skipped downward
# (a bare `object/` at root means "view3d, any type, object mode").
EDITOR_TOKENS = ("view3d", "geonodes", "shader", "image")
TYPE_TOKENS = (
    "mesh", "curve", "curves", "surface", "metaball", "text",
    "armature", "lattice", "empty", "greasepencil",
    "camera", "light", "speaker", "lightprobe", "volume", "pointcloud",
)
MODE_TOKENS = (
    "object", "edit", "pose", "sculpt",
    "vertex_paint", "weight_paint", "texture_paint", "particle",
)
# Fused type+mode shorthands, usable as a single folder anywhere a type
# segment would be valid (kept for backward compatibility with the flat
# layout): edit_mesh/ is exactly view3d + mesh + edit.
FUSED_TOKENS = {
    "edit_mesh": ("mesh", "edit"),
    "edit_curve": ("curve", "edit"),
    "edit_surface": ("surface", "edit"),
    "edit_text": ("text", "edit"),
    "edit_armature": ("armature", "edit"),
    "edit_metaball": ("metaball", "edit"),
    "edit_lattice": ("lattice", "edit"),
    "edit_greasepencil": ("greasepencil", "edit"),
}

# Canonical folder-name tokens. Order matters: alias collisions resolve
# to the earliest token in this tuple.
CONTEXT_TOKENS = EDITOR_TOKENS + TYPE_TOKENS + MODE_TOKENS + tuple(FUSED_TOKENS)

# Nesting span per token: (entry_level, exit_level). A segment is valid
# when its entry_level is deeper than the previous segment's exit_level.
_TOKEN_SPANS = {}
_TOKEN_SPANS.update({t: (1, 1) for t in EDITOR_TOKENS})
_TOKEN_SPANS.update({t: (2, 2) for t in TYPE_TOKENS})
_TOKEN_SPANS.update({t: (3, 3) for t in MODE_TOKENS})
_TOKEN_SPANS.update({t: (2, 3) for t in FUSED_TOKENS})

CHORDSONG_FILE = ".chordsong"

# bpy context.mode -> (mode token, implied object-type token or None)
_MODE_TOKENS_MAP = {
    "OBJECT": ("object", None),
    "EDIT_MESH": ("edit", "mesh"),
    "EDIT_CURVE": ("edit", "curve"),
    "EDIT_CURVES": ("edit", "curves"),
    "EDIT_SURFACE": ("edit", "surface"),
    "EDIT_TEXT": ("edit", "text"),
    "EDIT_ARMATURE": ("edit", "armature"),
    "EDIT_METABALL": ("edit", "metaball"),
    "EDIT_LATTICE": ("edit", "lattice"),
    "EDIT_GPENCIL": ("edit", "greasepencil"),
    "EDIT_GREASE_PENCIL": ("edit", "greasepencil"),
    "POSE": ("pose", "armature"),
    "SCULPT": ("sculpt", None),
    "SCULPT_CURVES": ("sculpt", "curves"),
    "SCULPT_GPENCIL": ("sculpt", "greasepencil"),
    "SCULPT_GREASE_PENCIL": ("sculpt", "greasepencil"),
    "PAINT_VERTEX": ("vertex_paint", "mesh"),
    "PAINT_WEIGHT": ("weight_paint", "mesh"),
    "PAINT_TEXTURE": ("texture_paint", "mesh"),
    "PARTICLE": ("particle", "mesh"),
}

# bpy Object.type -> object-type token
_OBJECT_TYPE_TOKENS = {
    "MESH": "mesh", "CURVE": "curve", "CURVES": "curves",
    "SURFACE": "surface", "META": "metaball", "FONT": "text",
    "ARMATURE": "armature", "LATTICE": "lattice", "EMPTY": "empty",
    "GPENCIL": "greasepencil", "GREASEPENCIL": "greasepencil",
    "CAMERA": "camera", "LIGHT": "light", "SPEAKER": "speaker",
    "LIGHT_PROBE": "lightprobe", "VOLUME": "volume",
    "POINTCLOUD": "pointcloud",
}


def script_contexts_for(space_type, tree_type=None, mode=None, active_object_type=None):
    """Token set matching an editor state. A script is visible when its
    folder path's tokens are a SUBSET of this set — so mesh edit mode
    ({view3d, mesh, edit}) matches view3d/, view3d/mesh/, view3d/edit/
    and view3d/mesh/edit/ folders at once."""
    if space_type == "VIEW_3D":
        tokens = {"view3d"}
        mode_token, implied_type = _MODE_TOKENS_MAP.get(mode or "", (None, None))
        if mode_token:
            tokens.add(mode_token)
        if implied_type:
            tokens.add(implied_type)
        type_token = _OBJECT_TYPE_TOKENS.get(active_object_type or "")
        if type_token:
            tokens.add(type_token)
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
    context_tokens: tuple        # () = visible in all contexts
    group: str                   # display group ("" = ungrouped)
    flagged: bool                # True = unrecognized/misordered folder (warn red)


def humanize_folder(name):
    """Group display name: the folder name as typed, minus the leading
    underscore marker of root-level all-context groups ('_my_tools' ->
    'my_tools'). No case or separator rewriting."""
    return name.lstrip("_").strip()


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


def _ignored(name):
    """Names starting with '__' or '.' are invisible to the scan entirely
    (files and directories, at every level): __pycache__, .git, .DS_Store,
    hidden editor droppings. The .chordsong config file is unaffected —
    it is read directly by path, not via directory enumeration."""
    return name.startswith(("__", "."))


def _is_script(dirpath, name):
    return (name.endswith(".py") and not _ignored(name)
            and os.path.isfile(os.path.join(dirpath, name)))


def _script_entries(dirpath, names, context_tokens, group, flagged):
    return [
        ScriptEntry(
            name=n[:-3],
            path=os.path.join(dirpath, n),
            context_tokens=tuple(context_tokens),
            group=group,
            flagged=flagged,
        )
        for n in names if _is_script(dirpath, n)
    ]


def _scan_group_folder(dirpath, rel, context_tokens, group, flagged, warnings):
    """One group folder: its scripts, warning for anything deeper."""
    names = _list_dir(dirpath, warnings)
    entries = _script_entries(dirpath, names, context_tokens, group, flagged)
    for deep in names:
        if os.path.isdir(os.path.join(dirpath, deep)) and not _ignored(deep):
            warnings.append(f"'{rel}/{deep}' is too deep — ignored")
    return entries


def _scan_context_dir(dirpath, rel, tokens, last_level, folder_to_token, warnings):
    """A context directory: scripts, deeper context segments (strict
    editor > type > mode order, levels skippable), and group folders."""
    entries = []
    names = _list_dir(dirpath, warnings)
    entries.extend(_script_entries(dirpath, names, tokens, "", False))
    for name in names:
        sub = os.path.join(dirpath, name)
        if not os.path.isdir(sub) or _ignored(name):
            continue
        sub_rel = f"{rel}/{name}" if rel else name
        token = folder_to_token.get(name.lower())
        if token is not None:
            entry_level, exit_level = _TOKEN_SPANS[token]
            if entry_level > last_level:
                # deeper context segment — descend
                entries.extend(_scan_context_dir(
                    sub, sub_rel, tokens + FUSED_TOKENS.get(token, (token,)),
                    exit_level, folder_to_token, warnings,
                ))
                continue
            # recognized token in the wrong position (e.g. object/mesh/):
            # flag loudly, keep scripts visible under the parent context
            warnings.append(
                f"'{sub_rel}' is out of order — nest editor > type > mode"
            )
            entries.extend(_scan_group_folder(
                sub, sub_rel, tokens, name, True, warnings))
            continue
        # plain group folder
        entries.extend(_scan_group_folder(
            sub, sub_rel, tokens, humanize_folder(name), False, warnings))
    return entries


def scan_scripts_folder(root):
    """Scan the scripts folder tree.

    Returns (entries, warnings). Never raises for malformed content —
    problems become warnings and, for unrecognized/misordered folders,
    flagged entries that stay visible.
    """
    entries = []
    warnings = []
    aliases, warnings_a = _load_aliases(root)
    warnings.extend(warnings_a)
    folder_to_token = _folder_token_map(aliases, warnings)

    root_names = _list_dir(root, warnings)
    entries.extend(_script_entries(root, root_names, (), "", False))

    for name in root_names:
        dirpath = os.path.join(root, name)
        if not os.path.isdir(dirpath) or _ignored(name):
            continue
        if name.startswith("_"):
            # explicit all-contexts group
            entries.extend(_scan_group_folder(
                dirpath, name, (), humanize_folder(name), False, warnings))
            continue
        token = folder_to_token.get(name.lower())
        if token is not None:
            _entry_level, exit_level = _TOKEN_SPANS[token]
            # A bare type/mode token at root implies the 3D viewport
            tokens = FUSED_TOKENS.get(token, (token,))
            if token not in EDITOR_TOKENS and "view3d" not in tokens:
                tokens = ("view3d",) + tokens
            entries.extend(_scan_context_dir(
                dirpath, name, tokens, exit_level, folder_to_token, warnings))
            continue
        # unrecognized root folder: flag loudly, keep scripts visible
        warnings.append(f"unrecognized folder '{name}'")
        entries.extend(_scan_group_folder(
            dirpath, name, (), name, True, warnings))

    return entries, warnings


def group_summaries(entries):
    """Distinct groups as (name, count, flagged) — flagged first, then A-Z.

    Feeds the scripts overlay's folders-first root view, where each group
    renders as an enterable folder row."""
    counts = {}
    flagged = {}
    for e in entries:
        if not e.group:
            continue
        counts[e.group] = counts.get(e.group, 0) + 1
        flagged[e.group] = flagged.get(e.group, False) or e.flagged
    return sorted(
        ((g, counts[g], flagged[g]) for g in counts),
        key=lambda t: (0 if t[2] else 1, t[0].lower()),
    )


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
