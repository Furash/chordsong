"""Tests for core/stats_store.py (pure statistics logic, no bpy)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stats_store import (  # noqa: E402
    blacklist_key,
    counts_to_data,
    data_to_counts,
    dump_blacklist,
    merge_counts,
    normalize_count,
    normalize_operator_idname,
    parse_blacklist,
    parse_operator_report,
)


def test_parse_operator_report_basic():
    msg = "bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD')"
    assert parse_operator_report(msg) == "mesh.primitive_cube_add"


def test_parse_operator_report_no_args():
    assert parse_operator_report("bpy.ops.object.delete()") == "object.delete"


def test_parse_operator_report_rejects_non_operator():
    assert parse_operator_report("Deleted 3 object(s)") is None
    assert parse_operator_report("Info: saved file") is None
    assert parse_operator_report("") is None
    assert parse_operator_report(None) is None


def test_parse_operator_report_rejects_malformed():
    # No parens
    assert parse_operator_report("bpy.ops.object.delete") is None
    # Empty idname
    assert parse_operator_report("bpy.ops.(x=1)") is None
    # Missing op segment
    assert parse_operator_report("bpy.ops.mesh(") is None
    # Property assignment, not an operator call
    assert parse_operator_report("bpy.ops.mesh.select_all.poll()") is None


def test_parse_operator_report_excludes_own_operators():
    assert parse_operator_report("bpy.ops.chordsong.leader()") is None
    # But exclusion is configurable
    assert parse_operator_report(
        "bpy.ops.chordsong.leader()", excluded_prefixes=()
    ) == "chordsong.leader"


def test_parse_operator_report_hard_excludes_run_script():
    # text.run_script fires for every chordsong script execution — never counted,
    # even with prefix exclusions disabled
    assert parse_operator_report("bpy.ops.text.run_script()") is None
    assert parse_operator_report("bpy.ops.text.run_script()", excluded_prefixes=()) is None


def test_data_to_counts_drops_run_script_entries():
    data = {"operators": {"text.run_script": 9, "TEXT_OT_run_script": 3, "mesh.bevel": 1}}
    assert data_to_counts(data)["operators"] == {"mesh.bevel": 1}


def test_normalize_count_legacy_dict_format():
    assert normalize_count({"count": 7}) == 7
    assert normalize_count(3) == 3
    assert normalize_count(2.0) == 2
    assert normalize_count("bogus") == 0
    assert normalize_count(None) == 0


def test_data_to_counts_ignores_metadata_and_junk():
    data = {
        "operators": {"mesh.bevel": 5, "legacy.op": {"count": 2}},
        "chords": {"g g": 1},
        "_metadata": {"blacklist": ["operators:x"]},
        "unknown_category": {"a": 1},
    }
    counts = data_to_counts(data)
    assert counts == {
        "operators": {"mesh.bevel": 5, "legacy.op": 2},
        "chords": {"g g": 1},
        "scripts": {},
        "properties": {},
    }


def test_data_to_counts_reads_scripts_category():
    data = {"scripts": {"NODE_Add.py": 4}}
    counts = data_to_counts(data)
    assert counts["scripts"] == {"NODE_Add.py": 4}


def test_normalize_operator_idname():
    assert normalize_operator_idname("VIEW3D_OT_move") == "view3d.move"
    assert normalize_operator_idname("mesh.bevel") == "mesh.bevel"
    assert normalize_operator_idname("weird") == "weird"
    # Already-dotted names pass through even if they contain _OT_
    assert normalize_operator_idname("mesh.thing_OT_x") == "mesh.thing_OT_x"


def test_data_to_counts_migrates_legacy_operator_keys():
    data = {
        "operators": {
            "VIEW3D_OT_move": 5,
            "view3d.move": 2,          # both forms present -> merged
            "CHORDSONG_OT_leader": 8,  # excluded after normalization
        },
        "chords": {},
    }
    counts = data_to_counts(data)
    assert counts["operators"] == {"view3d.move": 7}


def test_data_to_counts_handles_missing_categories():
    empty = {"operators": {}, "chords": {}, "scripts": {}, "properties": {}}
    assert data_to_counts({}) == empty
    assert data_to_counts({"operators": "corrupt"}) == empty


def test_merge_counts_sums_without_mutation():
    base = {"operators": {"a.b": 1}, "chords": {}}
    extra = {"operators": {"a.b": 2, "c.d": 3}, "chords": {"g": 1}}
    merged = merge_counts(base, extra)
    assert merged == {"operators": {"a.b": 3, "c.d": 3}, "chords": {"g": 1}, "scripts": {}, "properties": {}}
    assert base == {"operators": {"a.b": 1}, "chords": {}}


def test_counts_to_data_roundtrip():
    counts = {"operators": {"mesh.bevel": 4}, "chords": {"g g": 2}, "scripts": {"x.py": 1},
              "properties": {"space_data.clip_end": 3}}
    data = counts_to_data(counts, blacklist={"operators:x", "chords:y"}, last_saved="now")
    assert data["_metadata"]["blacklist"] == ["chords:y", "operators:x"]
    assert data["_metadata"]["last_saved"] == "now"
    assert data_to_counts(data) == counts


def test_blacklist_key_and_parse():
    key = blacklist_key("operators", "mesh.bevel")
    assert key == "operators:mesh.bevel"
    raw = dump_blacklist({key, "chords:g g"})
    parsed = parse_blacklist(raw)
    assert parsed == {"operators:mesh.bevel", "chords:g g"}


def test_parse_blacklist_tolerates_garbage():
    assert parse_blacklist("") == set()
    assert parse_blacklist(None) == set()
    assert parse_blacklist("not json") == set()
    assert parse_blacklist('{"a": 1}') == set()


def test_parse_property_report_basic():
    from core.stats_store import parse_property_report
    assert parse_property_report("bpy.context.space_data.clip_end = 996.7") == \
        ("space_data.clip_end", "996.7")
    assert parse_property_report("bpy.context.space_data.shading.type = 'RENDERED'") == \
        ("space_data.shading.type", "'RENDERED'")
    assert parse_property_report("bpy.context.scene.frame_current = 42") == \
        ("scene.frame_current", "42")


def test_parse_property_report_rejects_non_context():
    from core.stats_store import parse_property_report
    assert parse_property_report("bpy.data.objects['Cube'].location = (0, 0, 0)") is None
    assert parse_property_report("bpy.ops.mesh.select_all(action='SELECT')") is None
    assert parse_property_report("bpy.context.space_data.clip_end") is None  # no assignment
    assert parse_property_report("") is None
    assert parse_property_report(None) is None


def test_properties_category_roundtrip():
    from core.stats_store import data_to_counts, merge_counts
    counts = {"operators": {}, "chords": {}, "scripts": {},
              "properties": {"space_data.clip_end": 3}}
    data = counts_to_data(counts, property_values={"space_data.clip_end": "996.7"})
    assert data["properties"] == {"space_data.clip_end": 3}
    assert data["_metadata"]["property_values"] == {"space_data.clip_end": "996.7"}
    # loading and merging keep the category
    assert data_to_counts(data)["properties"] == {"space_data.clip_end": 3}
    merged = merge_counts(counts, {"properties": {"space_data.clip_end": 2}})
    assert merged["properties"] == {"space_data.clip_end": 5}


def test_properties_missing_in_legacy_files():
    from core.stats_store import data_to_counts
    legacy = {"operators": {"mesh.bevel": 1}, "chords": {}, "scripts": {}}
    assert data_to_counts(legacy)["properties"] == {}
