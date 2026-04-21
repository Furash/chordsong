"""Tests for collect_toggle_paths — pure helper, no bpy dependency."""

import sys
import os
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


def _run():
    passed = 0
    failed = 0

    def check(name, got, want):
        nonlocal passed, failed
        if got == want:
            passed += 1
        else:
            failed += 1
            print(f"FAIL {name}\n  got : {got!r}\n  want: {want!r}")

    # Valid single path
    m = FakeMapping(context_path="space_data.overlay.show_stats")
    check("valid_single_path", collect_toggle_paths(m), (["space_data.overlay.show_stats"], []))

    # Valid path + valid sub-items
    m = FakeMapping(
        context_path="space_data.overlay.show_stats",
        sub_items=[FakeSubItem("space_data.overlay.show_wireframes"), FakeSubItem("scene.use_gravity")],
    )
    check(
        "valid_path_plus_subitems",
        collect_toggle_paths(m),
        (
            [
                "space_data.overlay.show_stats",
                "space_data.overlay.show_wireframes",
                "scene.use_gravity",
            ],
            [],
        ),
    )

    # Bare name (no dot) at context_path → error
    m = FakeMapping(context_path="show_stats")
    valid, errs = collect_toggle_paths(m)
    check("bare_context_path_rejected_valid", valid, [])
    check("bare_context_path_rejected_has_error", len(errs), 1)
    check("bare_context_path_error_mentions_path", "show_stats" in errs[0], True)

    # Bare name in sub-items → error, other valid path kept
    m = FakeMapping(
        context_path="scene.use_gravity",
        sub_items=[FakeSubItem("bad_name"), FakeSubItem("space_data.overlay.show_stats")],
    )
    valid, errs = collect_toggle_paths(m)
    check("mixed_sub_items_valid", valid, ["scene.use_gravity", "space_data.overlay.show_stats"])
    check("mixed_sub_items_error_count", len(errs), 1)
    check("mixed_sub_items_error_mentions", "bad_name" in errs[0], True)

    # Whitespace-only paths are skipped, no error, no valid
    m = FakeMapping(context_path="   ", sub_items=[FakeSubItem("  ")])
    valid, errs = collect_toggle_paths(m)
    check("whitespace_only_no_valid", valid, [])
    check(
        "whitespace_only_has_no_content_error",
        any("no context path" in e for e in errs),
        True,
    )

    # Completely empty mapping returns "no context path" error
    m = FakeMapping()
    valid, errs = collect_toggle_paths(m)
    check("empty_mapping_no_valid", valid, [])
    check("empty_mapping_error", any("no context path" in e for e in errs), True)

    # Sub-item whitespace stripped before validation
    m = FakeMapping(context_path="  scene.use_gravity  ", sub_items=[FakeSubItem("  scene.frame_current  ")])
    check(
        "whitespace_stripped",
        collect_toggle_paths(m),
        (["scene.use_gravity", "scene.frame_current"], []),
    )

    # Missing sub_items attribute (None)
    @dataclass
    class MappingNoSub:
        context_path: str = "scene.use_gravity"

    check("missing_sub_items_attr", collect_toggle_paths(MappingNoSub()), (["scene.use_gravity"], []))

    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    _run()
