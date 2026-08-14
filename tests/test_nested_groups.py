"""Tests for nested group display (issue #18).

Group names may encode hierarchy with '|' separators, e.g.
"HardSurface | Kushiro". The overlay trims the common token-prefix at
each chord level and shows only the next distinguishing token. New
format tokens 'g*'/'G*' opt out of trimming and show full paths.

tokenizer.py is bpy-free and loaded by file path. layout.py uses
relative imports, so a minimal synthetic package is registered in
sys.modules (no __init__.py side effects executed — the addon's real
package inits import bpy).
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_by_path(name, rel_path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


tok = _load_by_path("cs_tokenizer_test", os.path.join("ui", "overlay", "tokenizer.py"))


def _load_layout():
    """Build a bare package skeleton so layout.py's relative imports resolve
    without executing the addon __init__ files (which need bpy)."""
    pkg = "cs_test_pkg"
    if pkg + ".ui.overlay.layout" in sys.modules:
        return sys.modules[pkg + ".ui.overlay.layout"]

    for name, path in [
        (pkg, ROOT),
        (pkg + ".core", os.path.join(ROOT, "core")),
        (pkg + ".ui", os.path.join(ROOT, "ui")),
        (pkg + ".ui.overlay", os.path.join(ROOT, "ui", "overlay")),
    ]:
        m = types.ModuleType(name)
        m.__path__ = [path]
        sys.modules[name] = m

    for name, rel in [
        (pkg + ".core.engine", os.path.join("core", "engine.py")),
        (pkg + ".ui.overlay.tokenizer", os.path.join("ui", "overlay", "tokenizer.py")),
        (pkg + ".ui.overlay.layout", os.path.join("ui", "overlay", "layout.py")),
    ]:
        spec = importlib.util.spec_from_file_location(
            name, os.path.join(ROOT, rel),
            submodule_search_locations=None)
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
    return sys.modules[pkg + ".ui.overlay.layout"]


# ---------------------------------------------------------------------------
# split_group_path
# ---------------------------------------------------------------------------

def test_split_group_path_splits_on_pipe_and_strips():
    assert tok.split_group_path("HardSurface | Kushiro") == ["HardSurface", "Kushiro"]


def test_split_group_path_flat_name():
    assert tok.split_group_path("Mesh") == ["Mesh"]


def test_split_group_path_empty():
    assert tok.split_group_path("") == []
    assert tok.split_group_path("  ") == []


def test_split_group_path_ignores_empty_segments():
    assert tok.split_group_path("A ||  B") == ["A", "B"]


# ---------------------------------------------------------------------------
# common_prefix_len
# ---------------------------------------------------------------------------

def test_common_prefix_len_shared_vendor_prefix():
    groups = ["HardSurface | Kushiro", "HardSurface | MACHIN3", "HardSurface | TeamC"]
    assert tok.common_prefix_len(groups) == 1


def test_common_prefix_len_mixed_level_is_zero():
    assert tok.common_prefix_len(["HardSurface | Kushiro", "Mesh"]) == 0


def test_common_prefix_len_single_nested_group_full_depth():
    assert tok.common_prefix_len(["HardSurface | Kushiro"]) == 2


def test_common_prefix_len_flat_identical():
    assert tok.common_prefix_len(["Mesh", "Mesh"]) == 1


def test_common_prefix_len_empty_and_blank_ignored():
    assert tok.common_prefix_len([]) == 0
    assert tok.common_prefix_len(["", "HardSurface | Kushiro"]) == 2


# ---------------------------------------------------------------------------
# trimmed formatting
# ---------------------------------------------------------------------------

def test_format_first_trims_prefix():
    got = tok._format_groups_first(["HardSurface | Kushiro"], prefix_len=1)
    assert got == "Kushiro"


def test_format_first_prefix_zero_shows_first_token():
    got = tok._format_groups_first(["HardSurface | Kushiro"], prefix_len=0)
    assert got == "HardSurface"


def test_format_first_keeps_last_token_when_prefix_covers_all():
    got = tok._format_groups_first(["HardSurface | Kushiro"], prefix_len=2)
    assert got == "Kushiro"


def test_format_first_flat_group_unchanged():
    assert tok._format_groups_first(["Mesh"], prefix_len=0) == "Mesh"
    assert tok._format_groups_first(["Mesh"], prefix_len=1) == "Mesh"


def test_format_first_unlabeled():
    assert tok._format_groups_first([], prefix_len=0) == "(unlabeled)"


def test_format_all_dedupes_after_trim():
    got = tok._format_groups_all(
        ["HardSurface | Kushiro", "HardSurface | MACHIN3"], prefix_len=0)
    assert got == "HardSurface"


def test_format_all_distinct_after_trim():
    got = tok._format_groups_all(
        ["HardSurface | Kushiro", "HardSurface | MACHIN3"], prefix_len=1)
    assert got == "Kushiro, MACHIN3"


def test_format_all_ellipsis_on_more_than_two_distinct():
    got = tok._format_groups_all(["A", "B", "C"], prefix_len=0)
    assert got == "A, B..."


# ---------------------------------------------------------------------------
# format tokens g / G / g* / G*
# ---------------------------------------------------------------------------

def _contents(tokens, ttype):
    return [t.content for t in tokens if t.type == ttype]


def test_folder_g_token_is_level_aware():
    tokens = tok.generate_tokens_for_folder(
        token_types=["C", "g"], chord="k", icon="",
        groups=["HardSurface | Kushiro"], count=3,
        separator_a="→", separator_b="::", group_prefix_len=1)
    assert _contents(tokens, "g") == ["Kushiro"]


def test_folder_g_star_shows_full_path():
    tokens = tok.generate_tokens_for_folder(
        token_types=["C", "g*"], chord="k", icon="",
        groups=["HardSurface | Kushiro"], count=3,
        separator_a="→", separator_b="::", group_prefix_len=1)
    assert _contents(tokens, "g*") == ["HardSurface | Kushiro"]


def test_folder_G_star_shows_all_full_paths():
    tokens = tok.generate_tokens_for_folder(
        token_types=["G*"], chord="k", icon="",
        groups=["HardSurface | Kushiro", "HardSurface | MACHIN3"], count=3,
        separator_a="→", separator_b="::", group_prefix_len=1)
    assert _contents(tokens, "G*") == ["HardSurface | Kushiro, HardSurface | MACHIN3"]


def test_item_g_token_is_level_aware():
    tokens = tok.generate_tokens_for_item(
        token_types=["C", "g", "L"], chord="g", icon="",
        groups=["HardSurface | Kushiro"], label="Grid Modeler",
        separator_a="→", separator_b="::", group_prefix_len=1)
    assert _contents(tokens, "g") == ["Kushiro"]


def test_item_g_star_shows_full_path():
    tokens = tok.generate_tokens_for_item(
        token_types=["g*"], chord="g", icon="",
        groups=["HardSurface | Kushiro"], label="Grid Modeler",
        separator_a="→", separator_b="::", group_prefix_len=1)
    assert _contents(tokens, "g*") == ["HardSurface | Kushiro"]


def test_flat_groups_render_identical_to_before():
    tokens = tok.generate_tokens_for_folder(
        token_types=["g", "G"], chord="a", icon="",
        groups=["Mesh"], count=2,
        separator_a="→", separator_b="::",
        group_prefix_len=tok.common_prefix_len(["Mesh", "Circle"]))
    assert _contents(tokens, "g") == ["Mesh"]
    assert _contents(tokens, "G") == ["Mesh"]


def test_group_prefix_len_defaults_to_zero():
    tokens = tok.generate_tokens_for_folder(
        token_types=["g"], chord="a", icon="", groups=["Mesh"], count=2,
        separator_a="→", separator_b="::")
    assert _contents(tokens, "g") == ["Mesh"]


# ---------------------------------------------------------------------------
# layout wiring: build_overlay_rows computes level prefix across candidates
# ---------------------------------------------------------------------------

class _FakePrefs:
    """Minimal prefs stand-in for build_overlay_rows."""
    def __init__(self):
        self.groups = []
        self.mappings = []
        self.overlay_item_format = "CUSTOM"
        self.overlay_separator_a = "→"
        self.overlay_separator_b = "::"
        self.overlay_format_folder = "C n s g"
        self.overlay_format_item = "C g L"
        self.overlay_sort_mode = "PRESET_C"
        self.overlay_max_label_length = 0


def _row_g_content(row, ttype="g"):
    return [t.content for t in row["tokens"] if t.type == ttype]


def test_layout_trims_shared_prefix_at_vendor_level():
    layout = _load_layout()
    engine = sys.modules["cs_test_pkg.core.engine"]
    cands = [
        engine.Candidate("k", "Kushiro tools", "HardSurface | Kushiro",
                         is_final=False, count=8, groups=("HardSurface | Kushiro",)),
        engine.Candidate("m", "MACHIN3 tools", "HardSurface | MACHIN3",
                         is_final=False, count=4, groups=("HardSurface | MACHIN3",)),
    ]
    rows, _footer = layout.build_overlay_rows(cands, has_buffer=True, p=_FakePrefs(),
                                              buffer_tokens=["4"])
    by_token = {r["token"]: r for r in rows}
    assert _row_g_content(by_token["k"]) == ["Kushiro"]
    assert _row_g_content(by_token["m"]) == ["MACHIN3"]


def test_layout_root_level_dedupes_to_top_token():
    layout = _load_layout()
    engine = sys.modules["cs_test_pkg.core.engine"]
    cands = [
        engine.Candidate("4", "HS", "HardSurface | Kushiro", is_final=False, count=15,
                         groups=("HardSurface | Kushiro", "HardSurface | MACHIN3")),
        engine.Candidate("b", "Mesh stuff", "Mesh", is_final=False, count=4,
                         groups=("Mesh",)),
    ]
    rows, _footer = layout.build_overlay_rows(cands, has_buffer=False, p=_FakePrefs())
    by_token = {r["token"]: r for r in rows}
    assert _row_g_content(by_token["4"]) == ["HardSurface"]
    assert _row_g_content(by_token["b"]) == ["Mesh"]


def test_layout_item_rows_trim_too():
    layout = _load_layout()
    engine = sys.modules["cs_test_pkg.core.engine"]
    cands = [
        engine.Candidate("g", "Grid Modeler", "HardSurface | Kushiro",
                         is_final=True, count=1, groups=("HardSurface | Kushiro",)),
        engine.Candidate("b", "Box Cutter", "HardSurface | MACHIN3",
                         is_final=True, count=1, groups=("HardSurface | MACHIN3",)),
    ]
    rows, _footer = layout.build_overlay_rows(cands, has_buffer=True, p=_FakePrefs(),
                                              buffer_tokens=["4", "k"])
    by_token = {r["token"]: r for r in rows}
    assert _row_g_content(by_token["g"]) == ["Kushiro"]
    assert _row_g_content(by_token["b"]) == ["MACHIN3"]
