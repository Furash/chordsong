"""Tests for scripts-overlay candidate building (build_scripts_candidates).

The scripts overlay bypasses candidates_for_prefix and builds Candidates
directly. It must carry the mapping's group into Candidate.groups —
dropping it made every row render the empty-groups "(unlabeled)"
fallback whenever the item format contains a g/G token.
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _load_layout():
    pkg = "cs_scripts_pkg"
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
        spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel))
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
    return sys.modules[pkg + ".ui.overlay.layout"]


class FakeMapping:
    def __init__(self, chord, label, group="", mapping_type="PYTHON_FILE"):
        self.chord = chord
        self.label = label
        self.group = group
        self.icon = ""
        self.enabled = True
        self.mapping_type = mapping_type


def test_numbered_item_carries_group():
    layout = _load_layout()
    cands = layout.build_scripts_candidates([FakeMapping("1", "My Script", group="Scripts")], [])
    assert len(cands) == 1
    assert cands[0].next_token == "1"
    assert cands[0].is_final is True
    assert cands[0].groups == ("Scripts",)


def test_display_only_item_carries_group():
    # Empty chord = beyond first 9, display-only
    layout = _load_layout()
    cands = layout.build_scripts_candidates([FakeMapping("", "Tail Script", group="MyFolder")], [])
    assert cands[0].next_token == ""
    assert cands[0].is_final is True
    assert cands[0].groups == ("MyFolder",)


def test_folder_entry_drops_group_to_avoid_label_duplication():
    # Folder rows label themselves "Name :: +N" with group=Name; carrying
    # the group would render the folder name twice on the row.
    layout = _load_layout()
    fm = FakeMapping("1", "MyFolder :: +3", group="MyFolder")
    fm.is_folder_entry = True
    cands = layout.build_scripts_candidates([fm], [])
    assert cands[0].groups == ()
    assert cands[0].group == ""


def test_ungrouped_item_has_empty_groups():
    layout = _load_layout()
    cands = layout.build_scripts_candidates([FakeMapping("1", "Loose", group="")], [])
    assert cands[0].groups == ()


def test_buffer_prefix_filters_and_carries_group():
    layout = _load_layout()
    maps = [
        FakeMapping("foo 1", "Match", group="Scripts"),
        FakeMapping("bar 1", "NoMatch", group="Scripts"),
    ]
    cands = layout.build_scripts_candidates(maps, ["foo"])
    assert [c.label for c in cands] == ["Match"]
    assert cands[0].groups == ("Scripts",)


def test_exact_match_is_final_with_group():
    layout = _load_layout()
    cands = layout.build_scripts_candidates([FakeMapping("foo", "Exact", group="Scripts")], ["foo"])
    assert cands[0].is_final is True
    assert cands[0].next_token == ""
    assert cands[0].groups == ("Scripts",)


def test_deeper_chord_yields_nonfinal_candidate():
    layout = _load_layout()
    cands = layout.build_scripts_candidates([FakeMapping("a b c", "Deep", group="Scripts")], ["a"])
    assert cands[0].is_final is False
    assert cands[0].next_token == "b"
    assert cands[0].groups == ("Scripts",)


def test_scripts_rows_show_group_not_unlabeled():
    """End to end: g token in item format renders the group name."""
    layout = _load_layout()

    class _FakePrefs:
        groups = []
        mappings = []
        overlay_item_format = "CUSTOM"
        overlay_separator_a = "→"
        overlay_separator_b = "::"
        overlay_format_folder = "C n s g"
        overlay_format_item = "C g L"
        overlay_sort_mode = "PRESET_C"
        overlay_max_label_length = 0

    folder = FakeMapping("1", "MyFolder :: +3", group="MyFolder")
    folder.is_folder_entry = True
    cands = layout.build_scripts_candidates(
        [folder,
         FakeMapping("2", "My Script", group="Scripts"),
         FakeMapping("3", "Other Script", group="Scripts")], [])
    rows, _ = layout.build_overlay_rows(cands, has_buffer=False, p=_FakePrefs(),
                                        is_scripts_overlay=True)
    g_by_row = {r["token"]: [t.content for t in r["tokens"] if t.type == "g"]
                for r in rows}
    # Folder row: label already names the folder — no group token, and
    # never the "(unlabeled)" placeholder (leader-overlay semantics only).
    assert g_by_row["1"] == []
    assert g_by_row["2"] == ["Scripts"]
    assert g_by_row["3"] == ["Scripts"]


def test_folder_row_counter_has_no_separator_prefix():
    layout = _load_layout()

    class _FakePrefs:
        groups = []
        mappings = []
        overlay_item_format = "CUSTOM"
        overlay_separator_a = "→"
        overlay_separator_b = "::"
        overlay_format_folder = "C n s g"
        overlay_format_item = "C g L"
        overlay_sort_mode = "PRESET_C"
        overlay_max_label_length = 0

    folder = FakeMapping("1", "MyFolder :: +3", group="MyFolder")
    folder.is_folder_entry = True
    cands = layout.build_scripts_candidates([folder], [])
    rows, _ = layout.build_overlay_rows(cands, has_buffer=False, p=_FakePrefs(),
                                        is_scripts_overlay=True)
    assert rows[0]["label_extra"] == "+3"


def test_uniform_group_suppressed_when_inside_folder():
    # Drilled into a folder every row shares that folder's group — the
    # header already names it, so rows drop the group token.
    layout = _load_layout()

    class _FakePrefs:
        groups = []
        mappings = []
        overlay_item_format = "CUSTOM"
        overlay_separator_a = "→"
        overlay_separator_b = "::"
        overlay_format_folder = "C n s g"
        overlay_format_item = "C g L"
        overlay_sort_mode = "PRESET_C"
        overlay_max_label_length = 0

    cands = layout.build_scripts_candidates(
        [FakeMapping("1", "Script A", group="MyFolder"),
         FakeMapping("2", "Script B", group="MyFolder")], [])
    rows, _ = layout.build_overlay_rows(cands, has_buffer=False, p=_FakePrefs(),
                                        is_scripts_overlay=True)
    assert all(t.type != "g" for r in rows for t in r["tokens"])

    # Mixed groups (e.g. search results across folders) keep the label.
    cands = layout.build_scripts_candidates(
        [FakeMapping("1", "Script A", group="FolderA"),
         FakeMapping("2", "Script B", group="FolderB")], [])
    rows, _ = layout.build_overlay_rows(cands, has_buffer=False, p=_FakePrefs(),
                                        is_scripts_overlay=True)
    g_contents = [t.content for r in rows for t in r["tokens"] if t.type == "g"]
    assert g_contents == ["FolderA", "FolderB"]


def test_leader_overlay_keeps_unlabeled_placeholder():
    layout = _load_layout()
    engine = sys.modules["cs_scripts_pkg.core.engine"]
    tokenizer = sys.modules["cs_scripts_pkg.ui.overlay.tokenizer"]
    tokens = tokenizer.generate_tokens_for_item(
        token_types=["g"], chord="a", icon="", groups=[], label="Thing",
        separator_a="→", separator_b="::")
    assert [t.content for t in tokens if t.type == "g"] == ["(unlabeled)"]
    assert engine is not None and layout is not None
