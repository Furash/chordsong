"""Tests for meta-operator handling in chord engine.

Verifies that chordsong.recents and chordsong.close_overlay are:
- Skipped by candidates_for_prefix (don't appear in overlay)
- Found by find_exact_mapping (can be matched and executed)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.engine import candidates_for_prefix, find_exact_mapping


class FakeMapping:
    """Minimal mapping object for testing."""
    def __init__(self, chord, operator="", enabled=True, mapping_type="OPERATOR"):
        self.chord = chord
        self.operator = operator
        self.enabled = enabled
        self.mapping_type = mapping_type
        self.label = operator
        self.icon = ""
        self.group = ""
        self.context = "ALL"


def test_candidates_skips_close_overlay():
    mappings = [
        FakeMapping("q", operator="chordsong.close_overlay"),
        FakeMapping("a", operator="mesh.primitive_cube_add"),
    ]
    cands = candidates_for_prefix(mappings, [])
    tokens = [c.next_token for c in cands]
    assert "q" not in tokens, "close_overlay should be skipped in candidates"
    assert "a" in tokens, "normal mapping should appear in candidates"


def test_candidates_skips_recents():
    mappings = [
        FakeMapping("r", operator="chordsong.recents"),
        FakeMapping("a", operator="mesh.primitive_cube_add"),
    ]
    cands = candidates_for_prefix(mappings, [])
    tokens = [c.next_token for c in cands]
    assert "r" not in tokens, "recents should be skipped in candidates"
    assert "a" in tokens, "normal mapping should appear in candidates"


def test_find_exact_mapping_finds_close_overlay():
    mappings = [
        FakeMapping("q", operator="chordsong.close_overlay"),
        FakeMapping("a", operator="mesh.primitive_cube_add"),
    ]
    m = find_exact_mapping(mappings, ["q"])
    assert m is not None, "find_exact_mapping should find close_overlay"
    assert m.operator == "chordsong.close_overlay"


def test_find_exact_mapping_finds_recents():
    mappings = [
        FakeMapping("space", operator="chordsong.recents"),
        FakeMapping("a", operator="mesh.primitive_cube_add"),
    ]
    m = find_exact_mapping(mappings, ["space"])
    assert m is not None, "find_exact_mapping should find recents"
    assert m.operator == "chordsong.recents"


def test_disabled_meta_operator_not_matched():
    mappings = [
        FakeMapping("q", operator="chordsong.close_overlay", enabled=False),
    ]
    m = find_exact_mapping(mappings, ["q"])
    assert m is None, "disabled mapping should not be found"


if __name__ == "__main__":
    test_candidates_skips_close_overlay()
    test_candidates_skips_recents()
    test_find_exact_mapping_finds_close_overlay()
    test_find_exact_mapping_finds_recents()
    test_disabled_meta_operator_not_matched()
    print("All meta-operator tests passed.")
