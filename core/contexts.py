"""Editor-context registry — the single source of truth for which Blender
editors (and editor modes) Chord Song runs in.

bpy-free by design (same layering rule as engine/config_io/script_scanner)
so the registry is unit-testable without Blender. Every enum, keymap list,
draw-handler space list and detection routine in the addon derives from
the tables below; add a context here and it appears everywhere.

Vocabulary:
  context token  — the value stored in ``mapping.context`` ("VIEW_3D",
                   "SEQUENCE_EDITOR", ...). "ALL" is a pseudo-token that
                   matches every editor and is not part of CONTEXTS.
  space type     — bpy ``Area.type`` / ``Space.type`` identifier. Several
                   tokens can share a space (3D View modes, Node Editor
                   tree types, Sequencer timeline vs preview), which is why
                   detection takes mode / tree / region hints.
  parent         — a sub-view of the same editor inherits its chords: the
                   Sequencer Preview also fires Video Sequencer chords, the
                   Timeline also fires Dope Sheet chords. The child context
                   exists for chords that should fire *only* there.
                   The 3D View is deliberately FLAT: Object, Sculpt, Paint,
                   Pose and the per-object-type Edit contexts are siblings,
                   so an Object-mode chord never fires in Sculpt or Edit.
                   The Movie Clip editor is flat the same way: Tracking,
                   Graph, Dope Sheet and Mask are siblings.
                   Use Global for a chord that should fire everywhere.
  group          — contexts sharing a group caption get a row of their own
                   in the Mappings-tab selector, under their editor's row
                   (the 3D View's eight Edit Modes).
  value          — stable enum value per token. Never renumber: Blender
                   stores EnumProperty values as ints in saved preferences.
"""

from dataclasses import dataclass
from typing import Optional

DEFAULT_CONTEXT = "VIEW_3D"
ALL_CONTEXT = "ALL"


@dataclass(frozen=True)
class EditorContext:
    token: str                     # mapping.context value
    label: str                     # UI label
    description: str               # UI tooltip
    icon: str                      # Blender icon identifier
    space_type: str                # bpy Area.type hosting this context
    script_token: str              # scripts-folder editor token (core.script_scanner)
    value: int                     # stable enum value (see module docstring)
    parent: Optional[str] = None   # editor context this context inherits from
    group: Optional[str] = None    # caption of the selector row it shares (see GROUP_ICONS)


# Display order (tabs, dialogs, "one mapping per context"): editor first,
# then its mode contexts. Values are stable ids, NOT positions.
CONTEXTS = (
    # 3D View — flat: no context here inherits from another.
    EditorContext("VIEW_3D", "3D View (Object)", "Active in 3D View Object Mode only",
                  "OBJECT_DATAMODE", "VIEW_3D", "view3d", 1),
    EditorContext("VIEW_3D_SCULPT", "3D View (Sculpt)", "Active in Sculpt modes (mesh, curves, Grease Pencil)",
                  "SCULPTMODE_HLT", "VIEW_3D", "view3d", 17),
    EditorContext("VIEW_3D_PAINT", "3D View (Paint)",
                  "Active in Vertex, Weight and Texture Paint and Grease Pencil draw modes",
                  "TPAINT_HLT", "VIEW_3D", "view3d", 18),
    EditorContext("VIEW_3D_POSE", "3D View (Pose)", "Active in Pose Mode",
                  "POSE_HLT", "VIEW_3D", "view3d", 19),
    EditorContext("EDIT_MESH", "Edit Mesh", "Active in Mesh Edit Mode",
                  "MESH_DATA", "VIEW_3D", "view3d", 25, group="Edit Modes"),
    EditorContext("EDIT_CURVE", "Edit Curve", "Active in Curve, Surface and Hair Curves Edit Mode",
                  "CURVE_DATA", "VIEW_3D", "view3d", 26, group="Edit Modes"),
    EditorContext("EDIT_ARMATURE", "Edit Armature", "Active in Armature Edit Mode",
                  "ARMATURE_DATA", "VIEW_3D", "view3d", 27, group="Edit Modes"),
    EditorContext("EDIT_TEXT", "Edit Text", "Active in Text Edit Mode",
                  "FONT_DATA", "VIEW_3D", "view3d", 28, group="Edit Modes"),
    EditorContext("EDIT_LATTICE", "Edit Lattice", "Active in Lattice Edit Mode",
                  "LATTICE_DATA", "VIEW_3D", "view3d", 29, group="Edit Modes"),
    EditorContext("EDIT_METABALL", "Edit Metaball", "Active in Metaball Edit Mode",
                  "META_DATA", "VIEW_3D", "view3d", 30, group="Edit Modes"),
    EditorContext("EDIT_GREASE_PENCIL", "Edit Grease Pencil", "Active in Grease Pencil Edit Mode",
                  "OUTLINER_DATA_GREASEPENCIL", "VIEW_3D", "view3d", 31, group="Edit Modes"),
    EditorContext("EDIT_POINTCLOUD", "Edit Point Cloud", "Active in Point Cloud Edit Mode",
                  "POINTCLOUD_DATA", "VIEW_3D", "view3d", 32, group="Edit Modes"),
    EditorContext("GEOMETRY_NODE", "Geometry Nodes", "Active in Geometry Nodes editor",
                  "GEOMETRY_NODES", "NODE_EDITOR", "geonodes", 3),
    EditorContext("SHADER_EDITOR", "Shader Editor", "Active in Shader Editor",
                  "NODE_MATERIAL", "NODE_EDITOR", "shader", 4),
    EditorContext("COMPOSITOR", "Compositor", "Active in Compositor node editor",
                  "NODE_COMPOSITING", "NODE_EDITOR", "compositor", 6),
    EditorContext("IMAGE_EDITOR", "UV Editor", "Active in UV / Image Editor (View, UV and Mask modes; inherited by Paint)",
                  "UV", "IMAGE_EDITOR", "image", 5),
    EditorContext("IMAGE_PAINT", "Image Paint", "Active in the Image Editor's Paint mode",
                  "TPAINT_HLT", "IMAGE_EDITOR", "image", 20, parent="IMAGE_EDITOR"),
    EditorContext("SEQUENCE_EDITOR", "Video Sequencer", "Active in the Video Sequencer (timeline; inherited by the Preview)",
                  "SEQUENCE", "SEQUENCE_EDITOR", "sequencer", 7),
    EditorContext("SEQUENCE_PREVIEW", "Sequencer Preview", "Active in the Video Sequencer Preview region",
                  "SEQ_PREVIEW", "SEQUENCE_EDITOR", "sequencer", 21, parent="SEQUENCE_EDITOR"),
    # Movie Clip — flat, like the 3D View: Tracking mode's Clip view, its
    # Graph and Dope Sheet views, and Mask mode are siblings.
    EditorContext("CLIP_EDITOR", "Movie Clip (Tracking)",
                  "Active in the Movie Clip editor's Tracking mode, Clip view",
                  "TRACKER", "CLIP_EDITOR", "clip", 8),
    EditorContext("CLIP_GRAPH", "Movie Clip (Graph)",
                  "Active in the Movie Clip editor's Graph view",
                  "GRAPH", "CLIP_EDITOR", "clip", 33),
    EditorContext("CLIP_DOPESHEET", "Movie Clip (Dope Sheet)",
                  "Active in the Movie Clip editor's Dope Sheet view",
                  "ACTION", "CLIP_EDITOR", "clip", 34),
    EditorContext("CLIP_MASK", "Movie Clip (Mask)",
                  "Active in the Movie Clip editor's Mask mode",
                  "MOD_MASK", "CLIP_EDITOR", "clip", 35),
    EditorContext("DOPESHEET_EDITOR", "Dope Sheet", "Active in Dope Sheet, Action Editor and other Dope Sheet modes (inherited by the Timeline)",
                  "ACTION", "DOPESHEET_EDITOR", "dopesheet", 9),
    EditorContext("TIMELINE", "Timeline", "Active in the Timeline",
                  "TIME", "DOPESHEET_EDITOR", "dopesheet", 22, parent="DOPESHEET_EDITOR"),
    EditorContext("GRAPH_EDITOR", "Graph Editor", "Active in the Graph Editor (F-Curves; inherited by Drivers)",
                  "GRAPH", "GRAPH_EDITOR", "graph", 10),
    EditorContext("GRAPH_DRIVERS", "Drivers", "Active in the Drivers editor",
                  "DRIVER", "GRAPH_EDITOR", "graph", 23, parent="GRAPH_EDITOR"),
    EditorContext("NLA_EDITOR", "NLA Editor", "Active in Nonlinear Animation editor",
                  "NLA", "NLA_EDITOR", "nla", 11),
)

# Values 0-5 are the ones Chord Song 1.2.9 actually shipped:
#   0 ALL, 1 VIEW_3D, 2 VIEW_3D_EDIT, 3 GEOMETRY_NODE, 4 SHADER_EDITOR,
#   5 IMAGE_EDITOR.
# Blender stores EnumProperty values as ints in saved preferences, so those
# six must keep their numbers forever and a retired one must never be handed
# to a different context — VIEW_3D_EDIT is gone, so 2 stays reserved.
# (Contexts added and dropped again inside this unreleased cycle never
# reached a user, so their numbers are free.)
RETIRED_VALUES = frozenset({2})

# Old token -> its closest surviving context, applied when a config is loaded
# (core.config_io) so chords saved under a retired token keep working.
LEGACY_CONTEXT_ALIASES = {
    "VIEW_3D_EDIT": "EDIT_MESH",
}

CONTEXT_TOKENS = tuple(c.token for c in CONTEXTS)
CONTEXT_BY_TOKEN = {c.token: c for c in CONTEXTS}
SUPPORTED_SPACE_TYPES = frozenset(c.space_type for c in CONTEXTS)
CONTEXT_PARENT = {c.token: c.parent for c in CONTEXTS}

# Editor families for the Mappings-tab context selector: one row per space
# type, listing that editor's contexts (base editor + its modes). Order =
# first appearance in CONTEXTS. Label/icon name the editor as a whole.
EDITOR_FAMILIES = (
    ("VIEW_3D", "3D View", "VIEW3D"),
    ("NODE_EDITOR", "Node Editor", "NODETREE"),
    ("IMAGE_EDITOR", "UV | Image Editor", "IMAGE"),
    ("SEQUENCE_EDITOR", "Video Sequencer", "SEQUENCE"),
    ("CLIP_EDITOR", "Movie Clip", "TRACKER"),
    ("DOPESHEET_EDITOR", "Dope Sheet", "ACTION"),
    ("GRAPH_EDITOR", "Graph Editor", "GRAPH"),
    ("NLA_EDITOR", "NLA Editor", "NLA"),
)

# Icon of a context group's selector row (EditorContext.group caption).
GROUP_ICONS = {
    "Edit Modes": "EDITMODE_HLT",
}

# Short labels for a context next to its editor's name ("3D View" →
# Object / Edit / Sculpt ...).
_SHORT_LABELS = {
    "VIEW_3D": "Object", "VIEW_3D_SCULPT": "Sculpt",
    "VIEW_3D_PAINT": "Paint", "VIEW_3D_POSE": "Pose",
    "EDIT_MESH": "Mesh", "EDIT_CURVE": "Curve", "EDIT_ARMATURE": "Armature",
    "EDIT_TEXT": "Text", "EDIT_LATTICE": "Lattice", "EDIT_METABALL": "Metaball",
    "EDIT_GREASE_PENCIL": "Grease Pencil", "EDIT_POINTCLOUD": "Point Cloud",
    "GEOMETRY_NODE": "Geometry", "SHADER_EDITOR": "Shader", "COMPOSITOR": "Compositor",
    "IMAGE_EDITOR": "UV / Image", "IMAGE_PAINT": "Paint",
    "SEQUENCE_EDITOR": "Timeline", "SEQUENCE_PREVIEW": "Preview",
    "CLIP_EDITOR": "Tracking", "CLIP_GRAPH": "Graph",
    "CLIP_DOPESHEET": "Dope Sheet", "CLIP_MASK": "Mask",
    "DOPESHEET_EDITOR": "Dope Sheet", "TIMELINE": "Timeline",
    "GRAPH_EDITOR": "F-Curves", "GRAPH_DRIVERS": "Drivers",
}


def family_contexts(space_type):
    """Contexts of one editor family in display order (base editor first)."""
    return tuple(c for c in CONTEXTS if c.space_type == space_type)


def context_short_label(token):
    """Label for a context next to its editor's name."""
    return _SHORT_LABELS.get(token) or context_label(token)

# Leader keymap per space: (Blender keymap name, space_type). Names must
# match keymaps Blender itself creates (see blender_default.py) or the
# addon keymap is never polled. Area-level "generic" keymaps are used
# where the editor has several regions (VSE timeline + preview, Clip).
LEADER_KEYMAPS = (
    ("3D View", "VIEW_3D"),
    ("Node Editor", "NODE_EDITOR"),
    ("Image", "IMAGE_EDITOR"),
    ("Video Sequence Editor", "SEQUENCE_EDITOR"),
    ("Clip", "CLIP_EDITOR"),
    ("Dopesheet", "DOPESHEET_EDITOR"),
    ("Graph Editor", "GRAPH_EDITOR"),
    ("NLA Editor", "NLA_EDITOR"),
)
LEADER_KEYMAP_NAMES = tuple(name for name, _ in LEADER_KEYMAPS)

# Display label per leader keymap (keyed by space_type) for the
# "Leader Key Bindings" section in preferences. Lists the editors that
# share the keymap so the user sees which bindings a row controls.
LEADER_KEYMAP_LABELS = {
    "VIEW_3D": "3D View",
    "NODE_EDITOR": "Node Editors",
    "IMAGE_EDITOR": "Image / UV Editor",
    "SEQUENCE_EDITOR": "Video Sequencer",
    "CLIP_EDITOR": "Movie Clip Editor",
    "DOPESHEET_EDITOR": "Dope Sheet / Timeline",
    "GRAPH_EDITOR": "Graph Editor / Drivers",
    "NLA_EDITOR": "NLA Editor",
}

# bpy.types class hosting overlay draw handlers, per space type.
SPACE_CLASS_NAMES = {
    "VIEW_3D": "SpaceView3D",
    "NODE_EDITOR": "SpaceNodeEditor",
    "IMAGE_EDITOR": "SpaceImageEditor",
    "SEQUENCE_EDITOR": "SpaceSequenceEditor",
    "CLIP_EDITOR": "SpaceClipEditor",
    "DOPESHEET_EDITOR": "SpaceDopeSheetEditor",
    "GRAPH_EDITOR": "SpaceGraphEditor",
    "NLA_EDITOR": "SpaceNLA",
}

# Region types that host overlay drawing, per space type. Every editor
# draws in its main WINDOW region; the VSE additionally has a PREVIEW
# region in the split "Sequencer & Preview" view.
OVERLAY_REGIONS = {
    "SEQUENCE_EDITOR": ("WINDOW", "PREVIEW"),
}
DEFAULT_OVERLAY_REGIONS = ("WINDOW",)

# Node-editor tree type -> context token. Unknown trees (Texture nodes,
# third-party trees) fall back to the Shader Editor context.
_NODE_TREE_CONTEXTS = {
    "GeometryNodeTree": "GEOMETRY_NODE",
    "ShaderNodeTree": "SHADER_EDITOR",
    "CompositorNodeTree": "COMPOSITOR",
}
_NODE_TREE_FALLBACK = "SHADER_EDITOR"

# 3D View: bpy.context.mode -> mode context. Anything not listed (OBJECT,
# PARTICLE, ...) is the Object context.
# bpy.context.mode -> per-object-type edit context. Modes not listed here
# (EDIT_POINTCLOUD, future ones) fall back to the generic Edit context via
# the "EDIT_" prefix below.
_VIEW3D_EDIT_MODES = {
    "EDIT_MESH": "EDIT_MESH",
    "EDIT_CURVE": "EDIT_CURVE",
    "EDIT_SURFACE": "EDIT_CURVE",
    "EDIT_CURVES": "EDIT_CURVE",
    "EDIT_ARMATURE": "EDIT_ARMATURE",
    "EDIT_TEXT": "EDIT_TEXT",
    "EDIT_LATTICE": "EDIT_LATTICE",
    "EDIT_METABALL": "EDIT_METABALL",
    "EDIT_GREASE_PENCIL": "EDIT_GREASE_PENCIL",
    "EDIT_GPENCIL": "EDIT_GREASE_PENCIL",
    "EDIT_POINTCLOUD": "EDIT_POINTCLOUD",
}
_VIEW3D_MODE_PREFIXES = (
    # An edit mode Blender adds later is closest to mesh editing — and must
    # not fall through to Object, whose chords never apply while editing.
    ("EDIT_", "EDIT_MESH"),
    ("SCULPT", "VIEW_3D_SCULPT"),
    ("PAINT_", "VIEW_3D_PAINT"),
    ("WEIGHT_", "VIEW_3D_PAINT"),
    ("VERTEX_", "VIEW_3D_PAINT"),
    ("POSE", "VIEW_3D_POSE"),
)

# Operator module prefix -> context token, used by the right-click "Add
# Chord Mapping" dialog to pre-select a context from the operator idname
# when the button lives outside its home editor.
OPERATOR_PREFIX_CONTEXTS = {
    "uv": "IMAGE_EDITOR",
    "image": "IMAGE_EDITOR",
    "sequencer": "SEQUENCE_EDITOR",
    "clip": "CLIP_EDITOR",
    "action": "DOPESHEET_EDITOR",
    "graph": "GRAPH_EDITOR",
    "nla": "NLA_EDITOR",
    "sculpt": "VIEW_3D_SCULPT",
    "paint": "VIEW_3D_PAINT",
    "pose": "VIEW_3D_POSE",
    "armature": "EDIT_ARMATURE",
    "font": "EDIT_TEXT",
    "lattice": "EDIT_LATTICE",
    "mball": "EDIT_METABALL",
}


def normalize_context(token, default=DEFAULT_CONTEXT):
    """Map any stored token to a context this build actually has.

    Retired tokens with a successor go there (LEGACY_CONTEXT_ALIASES);
    live tokens and the Global pseudo-token pass through; anything else —
    a context removed without a successor, a config written by a newer
    Chord Song, a hand-edited typo — falls back to ``default``.

    Total by design: the caller assigns the result to a Blender
    EnumProperty, which raises on an unknown identifier, and a raise inside
    the config loader costs the user every mapping after the bad one.
    """
    if not token:
        return default
    token = LEGACY_CONTEXT_ALIASES.get(token, token)
    if token == ALL_CONTEXT or token in CONTEXT_BY_TOKEN:
        return token
    return default


def contexts_in_group(space_type, group=None):
    """Contexts of one editor family that carry the given group
    caption (``None`` = the family's ungrouped contexts), in display order."""
    return tuple(c for c in CONTEXTS if c.space_type == space_type and c.group == group)


def group_captions(space_type):
    """Rollout body captions of one editor family, in display order."""
    seen = []
    for c in CONTEXTS:
        if c.space_type == space_type and c.group and c.group not in seen:
            seen.append(c.group)
    return tuple(seen)


def overlay_regions_for(space_type):
    """Region types where overlays draw for a given space type."""
    return OVERLAY_REGIONS.get(space_type, DEFAULT_OVERLAY_REGIONS)


def context_chain(token):
    """[token, parent, grandparent, ...] — the contexts whose chords are
    active when ``token`` is the live context (ALL excluded)."""
    chain = []
    seen = set()
    while token and token not in seen and token in CONTEXT_BY_TOKEN:
        chain.append(token)
        seen.add(token)
        token = CONTEXT_PARENT.get(token)
    if not chain and token:
        chain.append(token)  # unknown / ALL: itself
    return chain


def context_active_in(mapping_context, live_context):
    """True when a mapping bound to ``mapping_context`` fires while
    ``live_context`` is the detected editor context."""
    if mapping_context == ALL_CONTEXT:
        return True
    return mapping_context in context_chain(live_context)


def contexts_overlap(a, b):
    """True when chords in contexts ``a`` and ``b`` can both be active at
    once, i.e. the pair must be conflict-checked against each other."""
    if a == b or a == ALL_CONTEXT or b == ALL_CONTEXT:
        return True
    return a in context_chain(b) or b in context_chain(a)


def detect_context_token(space_type, tree_type=None, mode=None, *,
                         space_mode=None, view_type=None, region_type=None,
                         browse_mode=None):
    """Map live editor state to a context token.

    ``space_type`` is ``Space.type``; ``tree_type`` the Node Editor's tree
    type; ``mode`` is ``bpy.context.mode``; ``space_mode`` is the editor's
    own ``mode`` (Image: VIEW/UV/PAINT/MASK, Dope Sheet: ... /TIMELINE,
    Graph: FCURVES/DRIVERS, Clip: TRACKING/MASK); ``view_type`` is the
    Sequencer's ``view_type`` or the Clip editor's ``view``
    (CLIP/GRAPH/DOPESHEET) and, with ``region_type``, tells the Sequencer
    preview apart; ``browse_mode`` is FILES/ASSETS.
    Unknown spaces (Preferences, Top Bar, Text Editor, ...) fall back to
    DEFAULT_CONTEXT for backward compatibility.
    """
    if space_type == "VIEW_3D":
        m = mode or ""
        if m in _VIEW3D_EDIT_MODES:
            return _VIEW3D_EDIT_MODES[m]
        for prefix, token in _VIEW3D_MODE_PREFIXES:
            if m.startswith(prefix):
                return token
        return "VIEW_3D"
    if space_type == "NODE_EDITOR":
        return _NODE_TREE_CONTEXTS.get(tree_type or "", _NODE_TREE_FALLBACK)
    if space_type == "IMAGE_EDITOR":
        return "IMAGE_PAINT" if space_mode == "PAINT" else "IMAGE_EDITOR"
    if space_type == "SEQUENCE_EDITOR":
        if region_type == "PREVIEW" or view_type == "PREVIEW":
            return "SEQUENCE_PREVIEW"
        return "SEQUENCE_EDITOR"
    if space_type == "CLIP_EDITOR":
        # Mask mode always shows the clip; the view only matters in Tracking.
        if space_mode == "MASK":
            return "CLIP_MASK"
        if view_type == "GRAPH":
            return "CLIP_GRAPH"
        if view_type == "DOPESHEET":
            return "CLIP_DOPESHEET"
        return "CLIP_EDITOR"
    if space_type == "DOPESHEET_EDITOR":
        return "TIMELINE" if space_mode == "TIMELINE" else "DOPESHEET_EDITOR"
    if space_type == "GRAPH_EDITOR":
        return "GRAPH_DRIVERS" if space_mode == "DRIVERS" else "GRAPH_EDITOR"
    if space_type in SUPPORTED_SPACE_TYPES:
        return space_type
    return DEFAULT_CONTEXT


def context_label(token):
    """Human-readable label for a token ("ALL" and unknown tokens included)."""
    if token == ALL_CONTEXT:
        return "Global"
    ctx = CONTEXT_BY_TOKEN.get(token)
    return ctx.label if ctx else token


def tab_enum_items(counts=None):
    """Sidebar tab items for the Mappings preferences: "Global"
    first, then every editor context, each label suffixed with its
    mapping count when non-zero. ``counts`` maps token -> int (the ALL
    pseudo-token included). Values are the stable registry values so the
    enum keeps its identity while labels change.
    """
    counts = counts or {}

    def _label(base, token):
        n = counts.get(token, 0)
        return f"{base}  ({n})" if n else base

    items = [(ALL_CONTEXT, _label("Global", ALL_CONTEXT),
              "Global chords, active in every editor", "WORLD", 0)]
    for c in CONTEXTS:
        items.append((c.token, _label(c.label, c.token), c.description, c.icon, c.value))
    return items


def enum_items(include_all=False, icons=True, flags=False):
    """Build a static EnumProperty ``items`` tuple from the registry.

    include_all — prepend the "ALL" pseudo-context (WORLD icon, value 0).
    icons       — emit 5-tuples with icon and explicit value; otherwise
                  3-tuples (identifier, label, description).
    flags       — use power-of-two values for ``options={'ENUM_FLAG'}``.
                  Bits are POSITIONAL (1 << index), not derived from
                  ``value``: flag enums only live in dialogs, so their bits
                  need not be stable, and this keeps the 31-bit flag limit
                  off the registry's stable values.
    """
    items = []
    if include_all:
        if icons:
            items.append((ALL_CONTEXT, "Global", "Active in every editor context", "WORLD", 0))
        else:
            items.append((ALL_CONTEXT, "Global", "Active in every editor context"))
    for i, c in enumerate(CONTEXTS):
        if icons:
            value = (1 << i) if flags else c.value
            items.append((c.token, c.label, c.description, c.icon, value))
        else:
            items.append((c.token, c.label, c.description))
    return tuple(items)
