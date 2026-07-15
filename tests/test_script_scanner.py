"""Tests for core.script_scanner — bpy-free scripts folder scanning."""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.script_scanner import script_contexts_for


def test_contexts_view3d_object_mode():
    assert script_contexts_for("VIEW_3D", None, "OBJECT") == {"view3d", "object"}


def test_contexts_view3d_edit_mesh():
    assert script_contexts_for("VIEW_3D", None, "EDIT_MESH") == {"view3d", "edit", "edit_mesh"}


def test_contexts_view3d_edit_curve_variants():
    assert script_contexts_for("VIEW_3D", None, "EDIT_CURVE") == {"view3d", "edit", "edit_curve"}
    assert script_contexts_for("VIEW_3D", None, "EDIT_CURVES") == {"view3d", "edit", "edit_curve"}


def test_contexts_view3d_sculpt_and_paint():
    assert script_contexts_for("VIEW_3D", None, "SCULPT") == {"view3d", "sculpt"}
    assert script_contexts_for("VIEW_3D", None, "SCULPT_CURVES") == {"view3d", "sculpt"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_VERTEX") == {"view3d", "vertex_paint"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_WEIGHT") == {"view3d", "weight_paint"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_TEXTURE") == {"view3d", "texture_paint"}
    assert script_contexts_for("VIEW_3D", None, "PARTICLE") == {"view3d", "particle"}
    assert script_contexts_for("VIEW_3D", None, "POSE") == {"view3d", "pose"}


def test_contexts_view3d_unknown_mode_is_family_only():
    assert script_contexts_for("VIEW_3D", None, "SOME_FUTURE_MODE") == {"view3d"}
    assert script_contexts_for("VIEW_3D", None, None) == {"view3d"}


def test_contexts_node_editors():
    assert script_contexts_for("NODE_EDITOR", "GeometryNodeTree", "OBJECT") == {"geonodes"}
    assert script_contexts_for("NODE_EDITOR", "ShaderNodeTree", "OBJECT") == {"shader"}
    assert script_contexts_for("NODE_EDITOR", None, "OBJECT") == {"shader"}


def test_contexts_image_editor_and_unknown_space():
    assert script_contexts_for("IMAGE_EDITOR", None, "OBJECT") == {"image"}
    assert script_contexts_for("SEQUENCE_EDITOR", None, "OBJECT") == set()
    assert script_contexts_for("", None, None) == set()


from core.script_scanner import humanize_folder, scan_scripts_folder


def _touch(*parts):
    path = os.path.join(*parts)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# test script\n")


def _entry_map(entries):
    return {e.name: e for e in entries}


def test_humanize_folder():
    assert humanize_folder("_my_tools") == "My Tools"
    assert humanize_folder("my_bevel_scripts") == "My Bevel Scripts"
    assert humanize_folder("edit_meshh") == "Edit Meshh"


def test_scan_full_tree():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "a.py")
        _touch(root, "_my_tools", "b.py")
        _touch(root, "edit_mesh", "c.py")
        _touch(root, "edit_mesh", "my_bevels", "d.py")
        _touch(root, "edit_mesh", "my_bevels", "deeper", "x.py")
        _touch(root, "edit_meshh", "e.py")
        _touch(root, "__pycache__", "junk.py")
        _touch(root, "__ignored.py")

        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)

        assert set(m) == {"a", "b", "c", "d", "e"}
        assert m["a"].context_token is None and m["a"].group == "" and not m["a"].flagged
        assert m["b"].context_token is None and m["b"].group == "My Tools" and not m["b"].flagged
        assert m["c"].context_token == "edit_mesh" and m["c"].group == "" and not m["c"].flagged
        assert m["d"].context_token == "edit_mesh" and m["d"].group == "My Bevels" and not m["d"].flagged
        # unrecognized root folder: shown everywhere, raw folder name, flagged
        assert m["e"].context_token is None and m["e"].group == "edit_meshh" and m["e"].flagged
        # warnings: unrecognized root folder + too-deep dir
        assert any("edit_meshh" in w for w in warnings)
        assert any("deeper" in w for w in warnings)


def test_scan_group_inside_context_has_no_special_prefixes():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "edit_mesh", "_foo", "a.py")
        _touch(root, "edit_mesh", "geonodes", "b.py")
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        assert m["a"].context_token == "edit_mesh" and m["a"].group == "Foo"
        assert m["b"].context_token == "edit_mesh" and m["b"].group == "Geonodes"
        assert warnings == []


def test_scan_chordsong_alias_string_and_list():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            json.dump({"edit_mesh": "mesh", "geonodes": ["geo", "gn"]}, f)
        _touch(root, "mesh", "a.py")
        _touch(root, "geo", "b.py")
        _touch(root, "gn", "c.py")
        # default spelling was replaced, so edit_mesh/ is now unrecognized
        _touch(root, "edit_mesh", "d.py")
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        assert m["a"].context_token == "edit_mesh"
        assert m["b"].context_token == "geonodes"
        assert m["c"].context_token == "geonodes"
        assert m["d"].flagged and m["d"].context_token is None
        assert any("edit_mesh" in w for w in warnings)


def test_scan_chordsong_malformed_and_unknown_key():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            f.write("{not json")
        _touch(root, "edit_mesh", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert _entry_map(entries)["a"].context_token == "edit_mesh"  # defaults intact
        assert any(".chordsong" in w for w in warnings)

    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            json.dump({"nonsense_token": "x"}, f)
        entries, warnings = scan_scripts_folder(root)
        assert any("nonsense_token" in w for w in warnings)


def test_scan_alias_collision_first_token_wins():
    with tempfile.TemporaryDirectory() as root:
        # 'edit' comes before 'edit_mesh' in CONTEXT_TOKENS
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            json.dump({"edit": "shared", "edit_mesh": "shared"}, f)
        _touch(root, "shared", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert _entry_map(entries)["a"].context_token == "edit"
        assert any("shared" in w for w in warnings)


def test_scan_folder_names_case_insensitive():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "Edit_Mesh", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert _entry_map(entries)["a"].context_token == "edit_mesh"
        assert warnings == []


from core.script_scanner import ScriptEntry, sort_entries


def _e(name, group="", flagged=False):
    return ScriptEntry(name=name, path=f"/x/{name}.py", context_token=None,
                       group=group, flagged=flagged)


def test_sort_folders_first():
    entries = [_e("zeta"), _e("beta", group="Tools"), _e("alpha"),
               _e("gamma", group="Bevels"), _e("bad", group="typo_dir", flagged=True)]
    ordered = [e.name for e in sort_entries(entries, folders_first=True)]
    # flagged first, then grouped (groups A-Z, names A-Z), then ungrouped A-Z
    assert ordered == ["bad", "gamma", "beta", "alpha", "zeta"]


def test_sort_flat_when_folders_first_off():
    entries = [_e("zeta"), _e("beta", group="Tools"), _e("alpha"),
               _e("bad", group="typo_dir", flagged=True)]
    ordered = [e.name for e in sort_entries(entries, folders_first=False)]
    # flagged still first, rest flat name A-Z regardless of group
    assert ordered == ["bad", "alpha", "beta", "zeta"]
