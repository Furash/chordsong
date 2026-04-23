"""Tests for collect_toggle_paths — pure helper, no bpy."""
import os
import sys
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.engine import collect_toggle_paths


@dataclass
class FakeSubItem:
    path: str = ""


@dataclass
class FakeMapping:
    context_path: str = ""
    sub_items: List[FakeSubItem] = field(default_factory=list)


def test_valid_single_path():
    m = FakeMapping(context_path="space_data.overlay.show_stats")
    assert collect_toggle_paths(m) == (["space_data.overlay.show_stats"], [])


def test_valid_path_plus_sub_items():
    m = FakeMapping(
        context_path="space_data.overlay.show_stats",
        sub_items=[FakeSubItem("space_data.overlay.show_wireframes"), FakeSubItem("scene.use_gravity")],
    )
    valid, errors = collect_toggle_paths(m)
    assert valid == [
        "space_data.overlay.show_stats",
        "space_data.overlay.show_wireframes",
        "scene.use_gravity",
    ]
    assert errors == []


def test_bare_context_path_rejected():
    m = FakeMapping(context_path="show_stats")
    valid, errors = collect_toggle_paths(m)
    assert valid == []
    assert len(errors) == 1
    assert "show_stats" in errors[0]


def test_mixed_sub_items_keeps_valid_drops_bad():
    m = FakeMapping(
        context_path="scene.use_gravity",
        sub_items=[FakeSubItem("bad_name"), FakeSubItem("space_data.overlay.show_stats")],
    )
    valid, errors = collect_toggle_paths(m)
    assert valid == ["scene.use_gravity", "space_data.overlay.show_stats"]
    assert len(errors) == 1
    assert "bad_name" in errors[0]


def test_whitespace_only_paths_skipped():
    m = FakeMapping(context_path="   ", sub_items=[FakeSubItem("  ")])
    valid, errors = collect_toggle_paths(m)
    assert valid == []
    assert any("no context path" in e for e in errors)


def test_empty_mapping_has_error():
    m = FakeMapping()
    valid, errors = collect_toggle_paths(m)
    assert valid == []
    assert any("no context path" in e for e in errors)


def test_whitespace_stripped():
    m = FakeMapping(
        context_path="  scene.use_gravity  ",
        sub_items=[FakeSubItem("  scene.frame_current  ")],
    )
    assert collect_toggle_paths(m) == (["scene.use_gravity", "scene.frame_current"], [])


def test_missing_sub_items_attribute():
    @dataclass
    class MappingNoSub:
        context_path: str = "scene.use_gravity"

    assert collect_toggle_paths(MappingNoSub()) == (["scene.use_gravity"], [])
