"""Editor-context registry integrity, inheritance and detection (core.contexts, bpy-free)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.contexts import (  # noqa: E402
    ALL_CONTEXT,
    CONTEXTS,
    CONTEXT_BY_TOKEN,
    CONTEXT_PARENT,
    CONTEXT_TOKENS,
    DEFAULT_CONTEXT,
    EDITOR_FAMILIES,
    LEADER_KEYMAPS,
    LEADER_KEYMAP_LABELS,
    LEADER_KEYMAP_NAMES,
    LEGACY_CONTEXT_ALIASES,
    OPERATOR_PREFIX_CONTEXTS,
    RETIRED_VALUES,
    SPACE_CLASS_NAMES,
    SUPPORTED_SPACE_TYPES,
    context_active_in,
    context_chain,
    context_label,
    context_short_label,
    contexts_in_group,
    contexts_overlap,
    detect_context_token,
    enum_items,
    family_contexts,
    group_captions,
    normalize_context,
    overlay_regions_for,
    tab_enum_items,
)
from core.engine import filter_mappings_by_context  # noqa: E402
from core.script_scanner import EDITOR_TOKENS, script_contexts_for  # noqa: E402

# The enum values Chord Song 1.2.9 actually shipped. Blender saves enum
# values as ints in the user's preferences, so these must never change and
# a retired one (2, the generic Edit context) must never be reused.
# Guard against exactly the regression that reassigned 5 to the Compositor
# and would have re-pointed every saved UV Editor chord.
_FROZEN_VALUES = {
    "VIEW_3D": 1, "GEOMETRY_NODE": 3, "SHADER_EDITOR": 4, "IMAGE_EDITOR": 5,
}
# Tokens dropped during the 1.3 rework; their values stay reserved.
_RETIRED_TOKENS = ("VIEW_3D_EDIT", "OUTLINER", "PROPERTIES", "FILE_BROWSER",
                   "ASSET_BROWSER", "INFO", "SPREADSHEET")
# Only sub-views of one editor inherit; the 3D View is deliberately flat.
_CHILD_CONTEXTS = {
    "IMAGE_PAINT": "IMAGE_EDITOR", "SEQUENCE_PREVIEW": "SEQUENCE_EDITOR",
    "TIMELINE": "DOPESHEET_EDITOR", "GRAPH_DRIVERS": "GRAPH_EDITOR",
}
_VIEW3D_CONTEXTS = (
    "VIEW_3D", "VIEW_3D_SCULPT", "VIEW_3D_PAINT", "VIEW_3D_POSE",
    "EDIT_MESH", "EDIT_CURVE", "EDIT_ARMATURE", "EDIT_TEXT",
    "EDIT_LATTICE", "EDIT_METABALL", "EDIT_GREASE_PENCIL", "EDIT_POINTCLOUD",
)


def test_tokens_unique_and_all_reserved():
    assert len(set(CONTEXT_TOKENS)) == len(CONTEXT_TOKENS)
    assert ALL_CONTEXT not in CONTEXT_TOKENS
    assert DEFAULT_CONTEXT in CONTEXT_TOKENS
    assert set(CONTEXT_BY_TOKEN) == set(CONTEXT_TOKENS)
    assert len(CONTEXTS) == 25
    for tok in _RETIRED_TOKENS:
        assert tok not in CONTEXT_TOKENS, tok


def test_enum_values_stable_and_unique():
    values = [c.value for c in CONTEXTS]
    assert len(set(values)) == len(values)
    assert 0 not in values  # 0 is reserved for ALL
    for tok, val in _FROZEN_VALUES.items():
        assert CONTEXT_BY_TOKEN[tok].value == val, tok
    # A retired token's number is never handed to another context
    assert not (RETIRED_VALUES & set(values))
    # Nothing else may occupy a value the 1.2.9 release handed out
    shipped = {0: ALL_CONTEXT, 2: "VIEW_3D_EDIT", **{v: k for k, v in _FROZEN_VALUES.items()}}
    for c in CONTEXTS:
        assert shipped.get(c.value, c.token) == c.token, f"{c.token} took value {c.value}"


def test_flag_enum_bits_are_positional():
    # Flag enums live only in dialogs, so bits follow display order rather
    # than the stable values — that keeps the 31-bit cap off the registry.
    assert len(CONTEXTS) <= 31
    flags = [item[4] for item in enum_items(icons=True, flags=True)]
    assert flags == [1 << i for i in range(len(CONTEXTS))]


def test_enum_items_shapes():
    plain = enum_items(icons=False)
    assert all(len(item) == 3 for item in plain)
    assert [item[0] for item in plain] == list(CONTEXT_TOKENS)

    with_all = enum_items(include_all=True, icons=True)
    assert with_all[0][0] == ALL_CONTEXT and with_all[0][4] == 0
    values = [item[4] for item in with_all]
    assert len(set(values)) == len(values)
    assert all(len(item) == 5 for item in with_all)


def test_only_sub_views_inherit():
    parents = {c.token: c.parent for c in CONTEXTS if c.parent}
    assert parents == _CHILD_CONTEXTS
    for tok, parent in _CHILD_CONTEXTS.items():
        assert CONTEXT_BY_TOKEN[tok].space_type == CONTEXT_BY_TOKEN[parent].space_type
        assert context_chain(tok) == [tok, parent]
        # Children come after their parent in display order
        assert list(CONTEXT_TOKENS).index(tok) > list(CONTEXT_TOKENS).index(parent)
    assert context_chain(ALL_CONTEXT) == [ALL_CONTEXT]


def test_view3d_is_flat():
    # Object mode never leaks into Sculpt, Paint, Pose or any Edit context,
    # and no 3D View context inherits from another.
    for tok in _VIEW3D_CONTEXTS:
        assert CONTEXT_PARENT[tok] is None, tok
        assert context_chain(tok) == [tok], tok
    for tok in _VIEW3D_CONTEXTS:
        for other in _VIEW3D_CONTEXTS:
            assert contexts_overlap(tok, other) is (tok == other), (tok, other)
    assert not context_active_in("VIEW_3D", "VIEW_3D_SCULPT")
    assert not context_active_in("VIEW_3D", "EDIT_MESH")
    assert not context_active_in("EDIT_MESH", "EDIT_CURVE")
    assert context_active_in(ALL_CONTEXT, "VIEW_3D_SCULPT")


def test_context_active_in():
    assert context_active_in("SEQUENCE_EDITOR", "SEQUENCE_PREVIEW")
    assert context_active_in("SEQUENCE_PREVIEW", "SEQUENCE_PREVIEW")
    assert context_active_in(ALL_CONTEXT, "SEQUENCE_PREVIEW")
    assert not context_active_in("SEQUENCE_PREVIEW", "SEQUENCE_EDITOR")  # never upward
    assert not context_active_in("TIMELINE", "GRAPH_DRIVERS")            # unrelated


def test_contexts_overlap_symmetric():
    pairs_true = [("ALL", "NLA_EDITOR"), ("GRAPH_EDITOR", "GRAPH_DRIVERS"),
                  ("IMAGE_EDITOR", "IMAGE_PAINT"), ("NLA_EDITOR", "NLA_EDITOR")]
    pairs_false = [("VIEW_3D", "VIEW_3D_EDIT"), ("VIEW_3D_SCULPT", "VIEW_3D_POSE"),
                   ("EDIT_MESH", "VIEW_3D"), ("SEQUENCE_PREVIEW", "TIMELINE")]
    for a, b in pairs_true:
        assert contexts_overlap(a, b) and contexts_overlap(b, a), (a, b)
    for a, b in pairs_false:
        assert not contexts_overlap(a, b) and not contexts_overlap(b, a), (a, b)


def test_filter_mappings_honours_inheritance():
    class M:
        def __init__(self, context):
            self.context = context

    maps = [M("VIEW_3D"), M("VIEW_3D_SCULPT"), M("EDIT_MESH"), M("ALL"), M("SEQUENCE_EDITOR")]
    # Flat 3D View: each context sees only its own chords plus Global
    assert [m.context for m in filter_mappings_by_context(maps, "VIEW_3D")] == ["VIEW_3D", "ALL"]
    assert [m.context for m in filter_mappings_by_context(maps, "VIEW_3D_SCULPT")] == ["VIEW_3D_SCULPT", "ALL"]
    assert [m.context for m in filter_mappings_by_context(maps, "EDIT_MESH")] == ["EDIT_MESH", "ALL"]
    assert [m.context for m in filter_mappings_by_context(maps, "EDIT_CURVE")] == ["ALL"]
    # Sub-views still inherit their editor
    assert [m.context for m in filter_mappings_by_context(maps, "SEQUENCE_PREVIEW")] == ["ALL", "SEQUENCE_EDITOR"]


def test_legacy_aliases_point_at_live_contexts():
    assert LEGACY_CONTEXT_ALIASES["VIEW_3D_EDIT"] == "EDIT_MESH"
    for old, new in LEGACY_CONTEXT_ALIASES.items():
        assert old not in CONTEXT_TOKENS, old
        assert new in CONTEXT_TOKENS, new
        assert normalize_context(old) == new
    # Live tokens and the Global pseudo-token pass through untouched
    assert normalize_context("VIEW_3D") == "VIEW_3D"
    assert normalize_context(ALL_CONTEXT) == ALL_CONTEXT


def test_normalize_context_is_total():
    # A token this build has no successor for must still resolve to a real
    # context: the result is assigned to a Blender EnumProperty, which
    # raises on an unknown identifier, and a raise inside the config loader
    # costs the user every mapping after the bad one.
    for gone in ("SPREADSHEET", "OUTLINER", "PROPERTIES", "FILE_BROWSER", "INFO",
                 "ASSET_BROWSER", "FROM_A_NEWER_VERSION", "typo", "", None):
        assert normalize_context(gone) == DEFAULT_CONTEXT, gone
    assert normalize_context("SPREADSHEET", default="EDIT_MESH") == "EDIT_MESH"
    # Every result is a token the enums actually offer
    for token in list(CONTEXT_TOKENS) + [ALL_CONTEXT, "gone", ""]:
        assert normalize_context(token) in set(CONTEXT_TOKENS) | {ALL_CONTEXT}


def test_every_space_has_keymap_and_space_class():
    keymap_spaces = {space for _, space in LEADER_KEYMAPS}
    assert keymap_spaces == SUPPORTED_SPACE_TYPES
    assert set(SPACE_CLASS_NAMES) == SUPPORTED_SPACE_TYPES
    assert len(set(LEADER_KEYMAP_NAMES)) == len(LEADER_KEYMAP_NAMES)
    assert set(LEADER_KEYMAP_LABELS) == keymap_spaces
    for ctx in CONTEXTS:
        assert ctx.icon and ctx.label and ctx.description
        assert ctx.space_type in SUPPORTED_SPACE_TYPES


def test_detect_view3d_modes():
    d = detect_context_token
    assert d("VIEW_3D", None, "OBJECT") == "VIEW_3D"
    assert d("VIEW_3D", None, "PARTICLE") == "VIEW_3D"
    assert d("VIEW_3D", None, None) == "VIEW_3D"
    for mode in ("SCULPT", "SCULPT_CURVES", "SCULPT_GREASE_PENCIL", "SCULPT_GPENCIL"):
        assert d("VIEW_3D", None, mode) == "VIEW_3D_SCULPT", mode
    for mode in ("PAINT_VERTEX", "PAINT_WEIGHT", "PAINT_TEXTURE", "PAINT_GREASE_PENCIL",
                 "WEIGHT_GREASE_PENCIL", "VERTEX_GREASE_PENCIL", "PAINT_GPENCIL"):
        assert d("VIEW_3D", None, mode) == "VIEW_3D_PAINT", mode
    assert d("VIEW_3D", None, "POSE") == "VIEW_3D_POSE"


def test_detect_edit_modes_by_object_type():
    d = detect_context_token
    assert d("VIEW_3D", None, "EDIT_MESH") == "EDIT_MESH"
    for mode in ("EDIT_CURVE", "EDIT_SURFACE", "EDIT_CURVES"):
        assert d("VIEW_3D", None, mode) == "EDIT_CURVE", mode
    assert d("VIEW_3D", None, "EDIT_ARMATURE") == "EDIT_ARMATURE"
    assert d("VIEW_3D", None, "EDIT_TEXT") == "EDIT_TEXT"
    assert d("VIEW_3D", None, "EDIT_LATTICE") == "EDIT_LATTICE"
    assert d("VIEW_3D", None, "EDIT_METABALL") == "EDIT_METABALL"
    assert d("VIEW_3D", None, "EDIT_POINTCLOUD") == "EDIT_POINTCLOUD"
    for mode in ("EDIT_GREASE_PENCIL", "EDIT_GPENCIL"):
        assert d("VIEW_3D", None, mode) == "EDIT_GREASE_PENCIL", mode
    # An edit mode Blender adds later lands on mesh edit, never on Object
    assert d("VIEW_3D", None, "EDIT_SOMETHING_NEW") == "EDIT_MESH"


def test_detect_node_trees():
    assert detect_context_token("NODE_EDITOR", "GeometryNodeTree") == "GEOMETRY_NODE"
    assert detect_context_token("NODE_EDITOR", "ShaderNodeTree") == "SHADER_EDITOR"
    assert detect_context_token("NODE_EDITOR", "CompositorNodeTree") == "COMPOSITOR"
    # Texture nodes / third-party trees keep the historical Shader fallback
    assert detect_context_token("NODE_EDITOR", "TextureNodeTree") == "SHADER_EDITOR"
    assert detect_context_token("NODE_EDITOR", None) == "SHADER_EDITOR"


def test_detect_editor_sub_modes():
    d = detect_context_token
    assert d("IMAGE_EDITOR", space_mode="PAINT") == "IMAGE_PAINT"
    for m in ("VIEW", "UV", "MASK", None):
        assert d("IMAGE_EDITOR", space_mode=m) == "IMAGE_EDITOR", m
    assert d("SEQUENCE_EDITOR", region_type="PREVIEW") == "SEQUENCE_PREVIEW"
    assert d("SEQUENCE_EDITOR", view_type="PREVIEW", region_type="WINDOW") == "SEQUENCE_PREVIEW"
    assert d("SEQUENCE_EDITOR", view_type="SEQUENCER_PREVIEW", region_type="WINDOW") == "SEQUENCE_EDITOR"
    assert d("SEQUENCE_EDITOR", view_type="SEQUENCER") == "SEQUENCE_EDITOR"
    assert d("DOPESHEET_EDITOR", space_mode="TIMELINE") == "TIMELINE"
    for m in ("DOPESHEET", "ACTION", "SHAPEKEY", "GPENCIL", "MASK", "CACHEFILE", None):
        assert d("DOPESHEET_EDITOR", space_mode=m) == "DOPESHEET_EDITOR", m
    assert d("GRAPH_EDITOR", space_mode="DRIVERS") == "GRAPH_DRIVERS"
    assert d("GRAPH_EDITOR", space_mode="FCURVES") == "GRAPH_EDITOR"


def test_detect_plain_editors_map_to_own_token():
    for space in ("CLIP_EDITOR", "NLA_EDITOR"):
        assert detect_context_token(space) == space, space


def test_detect_unknown_space_falls_back():
    # Unsupported editors (incl. the retired Outliner / Properties / File
    # Browser / Info / Spreadsheet) fall back to the default context
    for space in ("PREFERENCES", "TEXT_EDITOR", "CONSOLE", "TOPBAR", "STATUSBAR",
                  "OUTLINER", "PROPERTIES", "FILE_BROWSER", "INFO", "SPREADSHEET", None, ""):
        assert detect_context_token(space) == DEFAULT_CONTEXT, space
        assert detect_context_token(space, browse_mode="ASSETS") == DEFAULT_CONTEXT, space


def test_overlay_regions():
    assert overlay_regions_for("VIEW_3D") == ("WINDOW",)
    assert set(overlay_regions_for("SEQUENCE_EDITOR")) == {"WINDOW", "PREVIEW"}


def test_operator_prefix_hints_point_at_registered_contexts():
    for token in OPERATOR_PREFIX_CONTEXTS.values():
        assert token in CONTEXT_TOKENS


def test_editor_families_cover_every_context_once():
    seen = []
    for space_type, label, icon in EDITOR_FAMILIES:
        assert label and icon
        members = family_contexts(space_type)
        assert members, space_type
        assert all(c.space_type == space_type for c in members)
        seen.extend(c.token for c in members)
    assert sorted(seen) == sorted(CONTEXT_TOKENS)
    assert [s for s, _, _ in EDITOR_FAMILIES] == list(dict.fromkeys(c.space_type for c in CONTEXTS))
    assert context_short_label("VIEW_3D_SCULPT") == "Sculpt"
    assert context_short_label("EDIT_GREASE_PENCIL") == "Grease Pencil"
    assert context_short_label("NLA_EDITOR") == "NLA Editor"  # falls back to the full label


def test_rollout_groups_partition_each_family():
    for space_type, _, _ in EDITOR_FAMILIES:
        members = list(family_contexts(space_type))
        collected = list(contexts_in_group(space_type))
        for caption in group_captions(space_type):
            grouped = contexts_in_group(space_type, caption)
            assert grouped, caption
            collected.extend(grouped)
        # Every context of the family is drawn exactly once, in order
        assert [c.token for c in collected] == [c.token for c in members], space_type
    # The 3D View groups its per-object-type edit contexts
    assert group_captions("VIEW_3D") == ("Edit Modes",)
    assert [c.token for c in contexts_in_group("VIEW_3D")] == [
        "VIEW_3D", "VIEW_3D_SCULPT", "VIEW_3D_PAINT", "VIEW_3D_POSE"]
    assert all(c.token.startswith("EDIT_") for c in contexts_in_group("VIEW_3D", "Edit Modes"))
    assert group_captions("NLA_EDITOR") == ()


def test_context_label():
    assert context_label(ALL_CONTEXT) == "Global"
    assert context_label("SEQUENCE_EDITOR") == "Video Sequencer"
    assert context_label("BOGUS") == "BOGUS"


def test_tab_enum_items_counts_and_order():
    items = tab_enum_items({"VIEW_3D": 12, ALL_CONTEXT: 3})
    ids = [i[0] for i in items]
    assert ids == [ALL_CONTEXT] + list(CONTEXT_TOKENS)
    labels = {i[0]: i[1] for i in items}
    assert labels[ALL_CONTEXT] == "Global  (3)"
    assert labels["VIEW_3D"] == "3D View (Object)  (12)"
    assert labels["SEQUENCE_EDITOR"] == "Video Sequencer"  # zero count → bare label
    # Values are the stable registry values regardless of counts
    values_a = [i[4] for i in items]
    values_b = [i[4] for i in tab_enum_items()]
    assert values_a == values_b == [0] + [c.value for c in CONTEXTS]
    assert all(len(i) == 5 and i[3] for i in items)


def test_script_editor_tokens_follow_registry():
    assert set(EDITOR_TOKENS) == {c.script_token for c in CONTEXTS}
    assert len(set(EDITOR_TOKENS)) == len(EDITOR_TOKENS)
    assert script_contexts_for("SEQUENCE_EDITOR") == {"sequencer"}
    assert script_contexts_for("NODE_EDITOR", "CompositorNodeTree") == {"compositor"}
    assert script_contexts_for("GRAPH_EDITOR") == {"graph"}
    assert script_contexts_for("CLIP_EDITOR") == {"clip"}
    # Retired editors keep no folder token
    for space in ("PREFERENCES", "TEXT_EDITOR", "PROPERTIES", "SPREADSHEET"):
        assert script_contexts_for(space) == set(), space
