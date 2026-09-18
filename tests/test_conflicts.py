"""Indexed conflict map (core.conflicts) — correctness and parity.

The index replaced a pairwise scan that re-split every chord string on every
redraw. These tests pin the behaviour it has to keep, and check it against a
deliberately naive reference over randomised data.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conflicts import (  # noqa: E402
    build_conflict_map,
    conflict_map,
    conflicted_indices,
    conflicts_with_any,
    contexts_with_conflicts,
    invalidate,
    is_conflicted,
    mappings_signature,
)
from core.contexts import contexts_overlap  # noqa: E402
from core.engine import split_chord  # noqa: E402


class M:
    def __init__(self, chord, context="VIEW_3D", enabled=True):
        self.chord = chord
        self.context = context
        self.enabled = enabled


def _reference(mappings):
    """The obvious O(n^2) answer, used only to check the index."""
    out = {}
    for i, a in enumerate(mappings):
        for j, b in enumerate(mappings):
            if i == j or not (a.enabled and b.enabled):
                continue
            ta, tb = tuple(split_chord(a.chord)), tuple(split_chord(b.chord))
            if not ta or not tb:
                continue
            if not contexts_overlap(a.context, b.context):
                continue
            if ta == tb or ta[:len(tb)] == tb or tb[:len(ta)] == ta:
                out.setdefault(i, set()).add(j)
    return out


def test_duplicate_in_same_context():
    maps = [M("g g"), M("g g"), M("x")]
    assert conflicted_indices(maps) == {0, 1}
    assert is_conflicted(maps, 0) and not is_conflicted(maps, 2)


def test_prefix_shadows_longer_chord():
    # "g" fires first, so "g g" can never be reached
    maps = [M("g"), M("g g")]
    assert conflicted_indices(maps) == {0, 1}
    assert conflict_map(maps)[0] == {1}


def test_unrelated_chords_and_contexts_are_clean():
    maps = [M("g g"), M("h h"), M("g g", context="SEQUENCE_EDITOR")]
    # Flat contexts: the Sequencer copy cannot fire beside the 3D View one
    assert conflicted_indices(maps) == set()


def test_global_clashes_with_every_editor():
    maps = [M("g g", context="ALL"), M("g g", context="NLA_EDITOR")]
    assert conflicted_indices(maps) == {0, 1}
    assert contexts_with_conflicts(maps) == {"ALL", "NLA_EDITOR"}


def test_sub_view_inherits_its_editors_chord():
    maps = [M("g g", context="SEQUENCE_EDITOR"), M("g g", context="SEQUENCE_PREVIEW")]
    assert conflicted_indices(maps) == {0, 1}


def test_disabled_and_chordless_never_conflict():
    maps = [M("g g"), M("g g", enabled=False), M(""), M("   ")]
    assert conflicted_indices(maps) == set()
    assert not is_conflicted(maps, 1)


def test_conflicts_with_any_targets_a_subset():
    # A Global chord clashing with one editor's chord, seen from that editor
    maps = [M("g g", context="ALL"), M("g g", context="NLA_EDITOR"), M("h", context="VIEW_3D")]
    cm = conflict_map(maps)
    assert conflicts_with_any(cm, 0, {1})
    assert not conflicts_with_any(cm, 0, {2})
    assert not conflicts_with_any(cm, 2, {0, 1})
    assert not conflicts_with_any({}, 0, {1})


def test_matches_the_naive_reference_on_random_data():
    contexts = ["ALL", "VIEW_3D", "VIEW_3D_SCULPT", "EDIT_MESH", "SEQUENCE_EDITOR",
                "SEQUENCE_PREVIEW", "GRAPH_EDITOR", "GRAPH_DRIVERS", "NLA_EDITOR"]
    letters = "abcd"
    rng = random.Random(20260918)
    for _ in range(60):
        maps = []
        for _ in range(rng.randint(0, 30)):
            length = rng.randint(1, 3)
            chord = " ".join(rng.choice(letters) for _ in range(length))
            maps.append(M(chord if rng.random() > 0.05 else "",
                          rng.choice(contexts), rng.random() > 0.15))
        invalidate()
        assert build_conflict_map(maps) == _reference(maps), [
            (m.chord, m.context, m.enabled) for m in maps]


def test_signature_tracks_every_field_that_matters():
    maps = [M("g g"), M("h")]
    before = mappings_signature(maps)
    maps[0].chord = "g h"
    assert mappings_signature(maps) != before
    maps[0].chord = "g g"
    assert mappings_signature(maps) == before
    maps[0].context = "NLA_EDITOR"
    assert mappings_signature(maps) != before
    maps[0].context = "VIEW_3D"
    maps[0].enabled = False
    assert mappings_signature(maps) != before


def test_cache_refreshes_when_a_mapping_changes():
    maps = [M("g g"), M("h")]
    invalidate()
    assert conflicted_indices(maps) == set()
    maps[1].chord = "g g"          # now a duplicate
    assert conflicted_indices(maps) == {0, 1}
    maps[1].enabled = False        # ...and now not
    assert conflicted_indices(maps) == set()
