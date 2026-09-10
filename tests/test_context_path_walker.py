"""Tests for bracket-aware context path splitting/resolution — pure, no bpy.

Toggle/property mappings used to walk `bpy.context` with getattr per
dot-separated part, so `preferences.addons["bl_ext.x.Y"].preferences.flag`
(bracket key, dots inside the key) could never resolve. These pin the new
tokenizer + walker.
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.context_path import (
    split_context_path,
    resolve_context_path,
    normalize_bpy_data_path,
)


class FakeCollection:
    """Mimics bpy_prop_collection: item access by name or index, no attrs."""

    def __init__(self, items):
        self._items = items

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self._items.values())[key]
        return self._items[key]


def _fake_context():
    univ = SimpleNamespace(preferences=SimpleNamespace(use_trims=False))
    return SimpleNamespace(
        space_data=SimpleNamespace(overlay=SimpleNamespace(show_stats=True)),
        preferences=SimpleNamespace(
            addons=FakeCollection({"bl_ext.user_default.UniV": univ})
        ),
    )


# --- split_context_path ---------------------------------------------------

def test_split_plain_dotted_path():
    assert split_context_path("space_data.overlay.show_stats") == [
        "space_data", "overlay", "show_stats",
    ]


def test_split_double_quoted_key_with_dots_inside():
    path = 'preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    assert split_context_path(path) == [
        "preferences", "addons", ("key", "bl_ext.user_default.UniV"),
        "preferences", "use_trims",
    ]


def test_split_single_quoted_key():
    assert split_context_path("scenes['My.Scene'].frame_current") == [
        "scenes", ("key", "My.Scene"), "frame_current",
    ]


def test_split_integer_index():
    assert split_context_path("screen.areas[1].spaces[0].show_region_ui") == [
        "screen", "areas", ("index", 1), "spaces", ("index", 0), "show_region_ui",
    ]


def test_split_rejects_unterminated_bracket():
    try:
        split_context_path('preferences.addons["x.preferences.flag')
    except ValueError:
        return
    raise AssertionError("expected ValueError for unterminated bracket")


# --- resolve_context_path -------------------------------------------------

def test_resolve_plain_path_returns_owner_and_prop():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, "space_data.overlay.show_stats")
    assert err is None
    assert owner is ctx.space_data.overlay
    assert prop == "show_stats"


def test_resolve_bracket_key_path_reaches_addon_prefs():
    ctx = _fake_context()
    path = 'preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    owner, prop, err = resolve_context_path(ctx, path)
    assert err is None
    assert owner is ctx.preferences.addons["bl_ext.user_default.UniV"].preferences
    assert prop == "use_trims"
    assert getattr(owner, prop) is False


def test_resolve_missing_attribute_reports_walked_prefix():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, "space_data.overlayy.show_stats")
    assert owner is None and prop is None
    assert "space_data.overlayy" in err


def test_resolve_missing_key_reports_key():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, 'preferences.addons["nope"].preferences.x')
    assert owner is None
    assert '"nope"' in err


def test_resolve_missing_final_property_reports_it():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, "space_data.overlay.show_statss")
    assert owner is None
    assert "show_statss" in err


def test_resolve_rejects_path_ending_in_bracket():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, 'preferences.addons["bl_ext.user_default.UniV"]')
    assert owner is None
    assert err


def test_resolve_rejects_bare_name():
    ctx = _fake_context()
    owner, prop, err = resolve_context_path(ctx, "show_stats")
    assert owner is None
    assert err


# --- normalize_bpy_data_path ----------------------------------------------

def test_normalize_strips_bpy_context_prefix():
    raw = 'bpy.context.preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    assert normalize_bpy_data_path(raw) == (
        'preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    )


def test_normalize_keeps_bracket_key_in_non_data_path():
    path = 'preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    assert normalize_bpy_data_path(path) == path


def test_normalize_still_singularizes_bpy_data_collections():
    assert normalize_bpy_data_path('bpy.data.worlds["World"].use_nodes') == "world.use_nodes"


# --- addon_prefs_context_path ---------------------------------------------

from utils.context_path import addon_prefs_context_path  # noqa: E402


class FakeRNA:
    def __init__(self, identifier, base_identifier):
        self.identifier = identifier
        self.base = SimpleNamespace(identifier=base_identifier) if base_identifier else None


class FakePrefs:
    """AddonPreferences stand-in. bl_idname on instances is garbage in real
    Blender, so identity must come from matching against the addons list."""

    def __init__(self, ptr, cls_name="UNIV_AddonPreferences"):
        self._ptr = ptr
        self.rna_type = FakeRNA(cls_name, "AddonPreferences")
        self.bl_idname = "\x06"

    def as_pointer(self):
        return self._ptr


def test_addon_prefs_path_built_from_matching_addon_entry():
    univ = FakePrefs(0x1)
    other = FakePrefs(0x2, "OTHER_Prefs")
    addons = [
        SimpleNamespace(module="bl_ext.user_default.Other", preferences=other),
        SimpleNamespace(module="bl_ext.user_default.UniV", preferences=univ),
        SimpleNamespace(module="bl_ext.blender_org.no_prefs", preferences=None),
    ]
    assert addon_prefs_context_path(univ, "use_trims", addons) == (
        'preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims'
    )


def test_addon_prefs_path_none_for_non_addon_pointer():
    overlay = SimpleNamespace(rna_type=FakeRNA("View3DOverlay", "bpy_struct"))
    assert addon_prefs_context_path(overlay, "show_stats", []) is None


def test_addon_prefs_path_none_when_no_addon_matches():
    orphan = FakePrefs(0x9)
    addons = [SimpleNamespace(module="bl_ext.user_default.UniV", preferences=FakePrefs(0x1))]
    assert addon_prefs_context_path(orphan, "flag", addons) is None


# --- is_operator_idname ---------------------------------------------------
# extract_from_button_pointer treated ANY pointer with a bl_idname as an
# operator. AddonPreferences instances expose a garbage bl_idname ("\x06" in
# Blender 5.2), so right-clicking an addon pref checkbox produced an operator
# mapping with an empty dialog instead of a toggle mapping.

from utils.context_path import is_operator_idname  # noqa: E402


def test_operator_idname_accepts_module_dot_name():
    assert is_operator_idname("mesh.primitive_monkey_add")
    assert is_operator_idname("uv.univ_weld")


def test_operator_idname_rejects_garbage_from_addon_prefs():
    assert not is_operator_idname("\x06")


def test_operator_idname_rejects_panel_and_menu_ids():
    assert not is_operator_idname("VIEW3D_PT_tools")
    assert not is_operator_idname("UNIV_MT_menu")


def test_operator_idname_rejects_empty_and_non_str():
    assert not is_operator_idname("")
    assert not is_operator_idname(None)
