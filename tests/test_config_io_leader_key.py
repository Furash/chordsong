"""Tests for leader-key round-trip in core/config_io.py (no bpy).

The leader key lives in Blender's keymap, not prefs, so config_io reaches
it through the engine wrapper functions. Tests monkeypatch those names on
the config_io module to run headless.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import config_io  # noqa: E402


class FakePrefs:
    """Minimal prefs stand-in: empty collections, defaults via getattr."""
    def __init__(self):
        self.mappings = []
        self.groups = []


def _patched(get_ret="SPACE", set_ret=True):
    """Patch leader accessors on config_io; return (calls, restore)."""
    calls = []
    orig_get = config_io.get_leader_key_type
    orig_set = config_io.set_leader_key_in_keymap
    config_io.get_leader_key_type = lambda: get_ret
    config_io.set_leader_key_in_keymap = lambda kt: calls.append(kt) or set_ret

    def restore():
        config_io.get_leader_key_type = orig_get
        config_io.set_leader_key_in_keymap = orig_set

    return calls, restore


def test_dump_prefs_includes_leader_key():
    _, restore = _patched(get_ret="TAB")
    try:
        data = config_io.dump_prefs(FakePrefs())
        assert data["leader_key"] == "TAB"
    finally:
        restore()


def test_dump_prefs_filtered_never_includes_leader_key():
    _, restore = _patched(get_ret="TAB")
    try:
        data = config_io.dump_prefs_filtered(FakePrefs(), {})
        assert "leader_key" not in data
    finally:
        restore()


def test_apply_config_ignores_leader_key_by_default():
    calls, restore = _patched()
    try:
        config_io.apply_config(FakePrefs(), {"leader_key": "TAB"})
        assert calls == []
    finally:
        restore()


def test_apply_config_sets_leader_key_when_opted_in():
    calls, restore = _patched()
    try:
        warns = config_io.apply_config(
            FakePrefs(), {"leader_key": "tab"}, apply_leader_key=True
        )
        assert calls == ["TAB"]  # normalized to upper
        assert any("leader" in w.lower() for w in warns)
    finally:
        restore()


def test_apply_config_reports_failure_to_set():
    calls, restore = _patched(set_ret=False)
    try:
        warns = config_io.apply_config(
            FakePrefs(), {"leader_key": "TAB"}, apply_leader_key=True
        )
        assert calls == ["TAB"]
        assert any("could not" in w.lower() for w in warns)
    finally:
        restore()


def test_apply_config_absent_key_is_noop():
    calls, restore = _patched()
    try:
        warns = config_io.apply_config(FakePrefs(), {}, apply_leader_key=True)
        assert calls == []
        assert warns == []
    finally:
        restore()


def test_apply_config_rejects_invalid_leader_values():
    calls, restore = _patched()
    try:
        for bad in ("", "   ", 5, None, ["TAB"], {"type": "TAB"}):
            config_io.apply_config(
                FakePrefs(), {"leader_key": bad}, apply_leader_key=True
            )
        assert calls == []
    finally:
        restore()


def test_append_config_never_touches_leader_key():
    calls, restore = _patched()
    try:
        config_io.apply_config_append(FakePrefs(), {"leader_key": "TAB"})
        assert calls == []
    finally:
        restore()
