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
