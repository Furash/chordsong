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
    assert script_contexts_for("VIEW_3D", None, "EDIT_MESH") == {"view3d", "edit", "mesh"}
    # active-object type is redundant here but harmless
    assert script_contexts_for("VIEW_3D", None, "EDIT_MESH", "MESH") == {"view3d", "edit", "mesh"}


def test_contexts_view3d_edit_curve_variants():
    assert script_contexts_for("VIEW_3D", None, "EDIT_CURVE") == {"view3d", "edit", "curve"}
    assert script_contexts_for("VIEW_3D", None, "EDIT_CURVES") == {"view3d", "edit", "curves"}


def test_contexts_view3d_sculpt_and_paint():
    assert script_contexts_for("VIEW_3D", None, "SCULPT", "MESH") == {"view3d", "sculpt", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "SCULPT_CURVES") == {"view3d", "sculpt", "curves"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_VERTEX") == {"view3d", "vertex_paint", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_WEIGHT") == {"view3d", "weight_paint", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "PAINT_TEXTURE") == {"view3d", "texture_paint", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "PARTICLE") == {"view3d", "particle", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "POSE") == {"view3d", "pose", "armature"}


def test_contexts_object_mode_active_type():
    assert script_contexts_for("VIEW_3D", None, "OBJECT", "MESH") == {"view3d", "object", "mesh"}
    assert script_contexts_for("VIEW_3D", None, "OBJECT", "ARMATURE") == {"view3d", "object", "armature"}
    assert script_contexts_for("VIEW_3D", None, "OBJECT", None) == {"view3d", "object"}


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
    # Folder names are shown as typed; only the root-group '_' marker is stripped.
    assert humanize_folder("_my_tools") == "my_tools"
    assert humanize_folder("my_bevel_scripts") == "my_bevel_scripts"
    assert humanize_folder("Edit_Meshh") == "Edit_Meshh"


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
        assert m["a"].context_tokens == () and m["a"].group == "" and not m["a"].flagged
        assert m["b"].context_tokens == () and m["b"].group == "my_tools" and not m["b"].flagged
        assert m["c"].context_tokens == ("view3d", "mesh", "edit") and m["c"].group == "" and not m["c"].flagged
        assert m["d"].context_tokens == ("view3d", "mesh", "edit") and m["d"].group == "my_bevels" and not m["d"].flagged
        # unrecognized root folder: shown everywhere, raw folder name, flagged
        assert m["e"].context_tokens == () and m["e"].group == "edit_meshh" and m["e"].flagged
        # warnings: unrecognized root folder + too-deep dir
        assert any("edit_meshh" in w for w in warnings)
        assert any("deeper" in w for w in warnings)


def test_scan_ignores_dot_directories():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, ".git", "hooks", "pre-commit.py")
        entries, warnings = scan_scripts_folder(root)
        assert entries == []
        assert warnings == []


def test_scan_ignores_dot_names_at_every_level():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, ".hidden.py")                          # dot file at root
        _touch(root, ".claude", "notes.py")                 # dot dir at root
        _touch(root, "edit_mesh", ".cache", "x.py")         # dot dir in context folder
        _touch(root, "edit_mesh", ".hidden.py")             # dot file in context folder
        _touch(root, "edit_mesh", "grp", ".deep", "y.py")   # dot dir at group level
        _touch(root, "edit_mesh", "grp", ".hidden.py")      # dot file in group folder
        _touch(root, "_tools", ".vscode", "z.py")           # dot dir in _group folder
        _touch(root, "edit_mesh", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert [e.name for e in entries] == ["a"]
        assert warnings == []  # no "too deep" or "unrecognized" noise from dot names


def test_scan_group_inside_context():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "edit_mesh", "_foo", "a.py")   # _ has no marker meaning below root
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        assert m["a"].context_tokens == ("view3d", "mesh", "edit") and m["a"].group == "foo"
        assert warnings == []


def test_scan_nested_context_paths():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "view3d", "mesh", "edit", "a.py")
        _touch(root, "view3d", "mesh", "object", "b.py")
        _touch(root, "view3d", "mesh", "edit", "my_bevels", "c.py")
        _touch(root, "mesh", "d.py")            # bare type at root implies view3d
        _touch(root, "object", "e.py")          # bare mode at root implies view3d
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        assert m["a"].context_tokens == ("view3d", "mesh", "edit")
        assert m["b"].context_tokens == ("view3d", "mesh", "object")
        assert m["c"].context_tokens == ("view3d", "mesh", "edit") and m["c"].group == "my_bevels"
        assert m["d"].context_tokens == ("view3d", "mesh")
        assert m["e"].context_tokens == ("view3d", "object")
        assert warnings == []


def test_scan_out_of_order_segments_flagged():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "object", "mesh", "a.py")      # mode then type: wrong order
        _touch(root, "edit_mesh", "geonodes", "b.py")  # editor after mode: wrong order
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        # scripts stay visible under the parent context, as flagged groups
        assert m["a"].context_tokens == ("view3d", "object") and m["a"].flagged
        assert m["a"].group == "mesh"
        assert m["b"].context_tokens == ("view3d", "mesh", "edit") and m["b"].flagged
        assert sum("out of order" in w for w in warnings) == 2


def test_scan_chordsong_alias_string_and_list():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            json.dump({"edit_mesh": "meshedit", "geonodes": ["geo", "gn"]}, f)
        _touch(root, "meshedit", "a.py")
        _touch(root, "geo", "b.py")
        _touch(root, "gn", "c.py")
        # default spelling was replaced, so edit_mesh/ is now unrecognized
        _touch(root, "edit_mesh", "d.py")
        entries, warnings = scan_scripts_folder(root)
        m = _entry_map(entries)
        assert m["a"].context_tokens == ("view3d", "mesh", "edit")
        assert m["b"].context_tokens == ("geonodes",)
        assert m["c"].context_tokens == ("geonodes",)
        assert m["d"].flagged and m["d"].context_tokens == ()
        assert any("edit_mesh" in w for w in warnings)


def test_scan_chordsong_malformed_and_unknown_key():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, ".chordsong"), "w", encoding="utf-8") as f:
            f.write("{not json")
        _touch(root, "edit_mesh", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert _entry_map(entries)["a"].context_tokens == ("view3d", "mesh", "edit")  # defaults intact
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
        assert _entry_map(entries)["a"].context_tokens == ("view3d", "edit")
        assert any("shared" in w for w in warnings)


def test_scan_folder_names_case_insensitive():
    with tempfile.TemporaryDirectory() as root:
        _touch(root, "Edit_Mesh", "a.py")
        entries, warnings = scan_scripts_folder(root)
        assert _entry_map(entries)["a"].context_tokens == ("view3d", "mesh", "edit")
        assert warnings == []


from core.script_scanner import ScriptEntry, sort_entries


def _e(name, group="", flagged=False):
    return ScriptEntry(name=name, path=f"/x/{name}.py", context_tokens=(),
                       group=group, flagged=flagged)


def test_sort_folders_first():
    entries = [_e("zeta"), _e("beta", group="Tools"), _e("alpha"),
               _e("gamma", group="Bevels"), _e("bad", group="typo_dir", flagged=True)]
    ordered = [e.name for e in sort_entries(entries, folders_first=True)]
    # flagged first, then grouped (groups A-Z, names A-Z), then ungrouped A-Z
    assert ordered == ["bad", "gamma", "beta", "alpha", "zeta"]


def test_group_summaries():
    from core.script_scanner import group_summaries
    entries = [_e("a"), _e("b", group="tools"), _e("c", group="tools"),
               _e("d", group="bevels"), _e("e", group="typo_dir", flagged=True)]
    assert group_summaries(entries) == [
        ("typo_dir", 1, True),   # flagged first
        ("bevels", 1, False),
        ("tools", 2, False),
    ]


def test_sort_flat_when_folders_first_off():
    entries = [_e("zeta"), _e("beta", group="Tools"), _e("alpha"),
               _e("bad", group="typo_dir", flagged=True)]
    ordered = [e.name for e in sort_entries(entries, folders_first=False)]
    # flagged still first, rest flat name A-Z regardless of group
    assert ordered == ["bad", "alpha", "beta", "zeta"]


# ---------------------------------------------------------------------------
# script_select_items — searchable list for chordsong.script_select
# ---------------------------------------------------------------------------

def test_select_items_includes_subfolder_scripts():
    from core.script_scanner import script_select_items
    entries = [_e("loose"), _e("aligner", group="shader"), _e("tool", group="my_tools")]
    items = script_select_items(entries)
    displays = [d for d, _p in items]
    assert "shader / aligner" in displays
    assert "my_tools / tool" in displays
    assert "loose" in displays
    # paths carried through
    assert dict(items)["shader / aligner"] == "/x/aligner.py"


def test_select_items_sorted_by_display():
    from core.script_scanner import script_select_items
    entries = [_e("zeta"), _e("beta", group="Tools"), _e("alpha")]
    displays = [d for d, _p in script_select_items(entries)]
    assert displays == sorted(displays, key=str.lower)


def test_select_items_query_matches_name_and_group():
    from core.script_scanner import script_select_items
    entries = [_e("aligner", group="shader"), _e("boxcut", group="view3d")]
    # match by name fragment
    assert [d for d, _p in script_select_items(entries, "align")] == ["shader / aligner"]
    # match by group fragment
    assert [d for d, _p in script_select_items(entries, "shader")] == ["shader / aligner"]
    # no match
    assert script_select_items(entries, "zzzz") == []
