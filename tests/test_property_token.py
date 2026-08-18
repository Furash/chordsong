"""Tests for the P item-format token (property value display).

The engine used to merge property values into the label as
"label ::  value", rendered unconditionally as label_extra. Now the
value stays in Candidate.property_value and renders only where the
item format string places a P token.
"""
import importlib.util
import os
import sys
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def _load_layout():
    pkg = "cs_ptoken_pkg"
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


class _FakePrefs:
    groups = []
    mappings = []
    overlay_item_format = "CUSTOM"
    overlay_separator_a = "→"
    overlay_separator_b = "::"
    overlay_format_folder = "C n s g"
    overlay_format_item = "C L P"
    overlay_sort_mode = "PRESET_C"
    overlay_max_label_length = 0


def _tokenizer():
    _load_layout()
    return sys.modules["cs_ptoken_pkg.ui.overlay.tokenizer"]


def _engine():
    _load_layout()
    return sys.modules["cs_ptoken_pkg.core.engine"]


def test_p_token_renders_property_value():
    tok = _tokenizer()
    tokens = tok.generate_tokens_for_item(
        token_types=["C", "L", "P"], chord="d", icon="",
        groups=[], label="Material", separator_a="→", separator_b="::",
        mapping_type="CONTEXT_PROPERTY", property_value="'MATERIAL'")
    assert [t.content for t in tokens if t.type == "P"] == ["'MATERIAL'"]
    # counter color preserves the old label_extra appearance
    assert [t.color_key for t in tokens if t.type == "P"] == ["overlay_color_counter"]


def test_p_token_skipped_when_no_value():
    tok = _tokenizer()
    tokens = tok.generate_tokens_for_item(
        token_types=["C", "L", "P"], chord="f", icon="",
        groups=[], label="Toggle Flat", separator_a="→", separator_b="::",
        mapping_type="CONTEXT_TOGGLE", property_value="")
    assert all(t.type != "P" for t in tokens)


def test_engine_no_longer_merges_value_into_label():
    engine = _engine()

    class FakeMapping:
        chord = "d"
        label = "Material"
        group = "Display"
        icon = ""
        enabled = True
        mapping_type = "CONTEXT_PROPERTY"
        context_path = "space_data.shading.color_type"
        property_value = "'MATERIAL'"
        order_index = 0

    cands = engine.candidates_for_prefix([FakeMapping()], [])
    assert len(cands) == 1
    assert cands[0].label == "Material"
    assert "::" not in cands[0].label
    assert cands[0].property_value == "'MATERIAL'"


def test_layout_property_row_uses_p_token_not_label_extra():
    layout = _load_layout()
    engine = _engine()
    cands = [engine.Candidate(
        "d", "Material", "Display", is_final=True, count=1,
        mapping_type="CONTEXT_PROPERTY", property_value="'MATERIAL'")]
    rows, _ = layout.build_overlay_rows(cands, has_buffer=True, p=_FakePrefs(),
                                        buffer_tokens=["v"])
    assert rows[0]["label_extra"] == ""
    assert [t.content for t in rows[0]["tokens"] if t.type == "P"] == ["'MATERIAL'"]


def test_layout_format_without_p_hides_value():
    layout = _load_layout()
    engine = _engine()

    class _NoP(_FakePrefs):
        overlay_format_item = "C L"

    cands = [engine.Candidate(
        "d", "Material", "Display", is_final=True, count=1,
        mapping_type="CONTEXT_PROPERTY", property_value="'MATERIAL'")]
    rows, _ = layout.build_overlay_rows(cands, has_buffer=True, p=_NoP(),
                                        buffer_tokens=["v"])
    assert rows[0]["label_extra"] == ""
    assert all(t.type != "P" for t in rows[0]["tokens"])
    assert "'MATERIAL'" not in [t.content for t in rows[0]["tokens"]]
