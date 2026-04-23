"""Tests for stash_panel_states / take_panel_states — pure dict handoff.

utils/panels.py top-imports bpy (transitively), so importing it directly
from this file would fail in a bpy-less environment. Mirror the two
functions here — they're 5 lines each and purely module-level dict ops.
Update both sides together if production changes.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- mirrored from utils/panels.py -------------------------------------
_PENDING_HANDOFF: dict = {}


def stash_panel_states(panel_states):
    _PENDING_HANDOFF.clear()
    if panel_states:
        _PENDING_HANDOFF.update(panel_states)


def take_panel_states():
    result = dict(_PENDING_HANDOFF)
    _PENDING_HANDOFF.clear()
    return result
# -----------------------------------------------------------------------


def _reset():
    _PENDING_HANDOFF.clear()


def test_stash_then_take_roundtrip():
    _reset()
    payload = {0xA: {"hud": True, "space_type": "VIEW_3D"}}
    stash_panel_states(payload)
    got = take_panel_states()
    assert got == payload


def test_take_clears_internal_dict():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    take_panel_states()
    # Module-level dict must now be empty.
    assert _PENDING_HANDOFF == {}


def test_take_returns_copy_not_reference():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    got = take_panel_states()
    got[0xB] = {"n_panel": False}
    # Mutating the returned dict must not affect the module dict (which is
    # empty anyway after take), nor a subsequent stash+take roundtrip.
    stash_panel_states({0xC: {"t_panel": True}})
    second = take_panel_states()
    assert second == {0xC: {"t_panel": True}}
    assert 0xB not in second


def test_stash_empty_dict_clears():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    stash_panel_states({})
    assert take_panel_states() == {}


def test_stash_none_clears():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    stash_panel_states(None)
    assert take_panel_states() == {}


def test_take_on_empty_returns_empty_dict():
    _reset()
    got = take_panel_states()
    assert got == {}
    assert isinstance(got, dict)


def test_take_twice_second_is_empty():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    first = take_panel_states()
    second = take_panel_states()
    assert first == {0xA: {"hud": True}}
    assert second == {}


def test_stash_overwrites_previous():
    _reset()
    stash_panel_states({0xA: {"hud": True}})
    stash_panel_states({0xB: {"n_panel": False}})
    got = take_panel_states()
    assert got == {0xB: {"n_panel": False}}
    assert 0xA not in got
