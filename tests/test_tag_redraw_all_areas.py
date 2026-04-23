"""Tests for tag_redraw_all_areas — pure loop over window.screen.area.

The helper lives in utils.redraw, which does NOT top-import bpy (it only
imports bpy lazily when context is None). So this module can be imported
directly. For the None-context branch we inject a minimal bpy stub into
sys.modules before calling, and restore afterwards.
"""
import os
import sys
import types
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.redraw import tag_redraw_all_areas


class FakeArea:
    def __init__(self, raise_on_redraw=False):
        self.redraw_count = 0
        self.raise_on_redraw = raise_on_redraw

    def tag_redraw(self):
        self.redraw_count += 1
        if self.raise_on_redraw:
            raise ReferenceError("area has been freed")


@dataclass
class FakeScreen:
    areas: List[FakeArea] = field(default_factory=list)


class FakeWindow:
    def __init__(self, screen=None, raise_on_screen=False):
        self._screen = screen
        self.raise_on_screen = raise_on_screen

    @property
    def screen(self):
        if self.raise_on_screen:
            raise RuntimeError("window is invalid")
        return self._screen


@dataclass
class FakeWindowManager:
    windows: List[FakeWindow] = field(default_factory=list)


@dataclass
class FakeContext:
    window_manager: FakeWindowManager = field(default_factory=FakeWindowManager)


def test_every_area_gets_tag_redraw():
    a1, a2, a3 = FakeArea(), FakeArea(), FakeArea()
    screen_a = FakeScreen(areas=[a1, a2])
    screen_b = FakeScreen(areas=[a3])
    wm = FakeWindowManager(windows=[FakeWindow(screen_a), FakeWindow(screen_b)])
    ctx = FakeContext(window_manager=wm)

    tag_redraw_all_areas(ctx)

    assert a1.redraw_count == 1
    assert a2.redraw_count == 1
    assert a3.redraw_count == 1


def test_raising_area_does_not_break_others():
    ok1 = FakeArea()
    bad = FakeArea(raise_on_redraw=True)
    ok2 = FakeArea()
    screen = FakeScreen(areas=[ok1, bad, ok2])
    wm = FakeWindowManager(windows=[FakeWindow(screen)])
    ctx = FakeContext(window_manager=wm)

    tag_redraw_all_areas(ctx)

    # All three are attempted; the raising one still increments its counter
    # before raising, and the others complete successfully.
    assert ok1.redraw_count == 1
    assert bad.redraw_count == 1
    assert ok2.redraw_count == 1


def test_raising_window_is_skipped_cleanly():
    good_area = FakeArea()
    good_screen = FakeScreen(areas=[good_area])
    bad_window = FakeWindow(raise_on_screen=True)
    good_window = FakeWindow(good_screen)
    wm = FakeWindowManager(windows=[bad_window, good_window])
    ctx = FakeContext(window_manager=wm)

    # Should not raise.
    tag_redraw_all_areas(ctx)
    assert good_area.redraw_count == 1


def test_none_screen_skipped():
    wm = FakeWindowManager(windows=[FakeWindow(screen=None)])
    ctx = FakeContext(window_manager=wm)

    # No areas; should simply no-op without raising.
    tag_redraw_all_areas(ctx)


def test_empty_window_manager_is_noop():
    ctx = FakeContext(window_manager=FakeWindowManager(windows=[]))
    tag_redraw_all_areas(ctx)  # Must not raise.


def test_none_context_falls_back_to_bpy_context():
    area = FakeArea()
    screen = FakeScreen(areas=[area])
    wm = FakeWindowManager(windows=[FakeWindow(screen)])

    # Build a minimal bpy module with bpy.context.window_manager.
    bpy_stub = types.ModuleType("bpy")
    bpy_stub.context = types.SimpleNamespace(window_manager=wm)

    # Save and restore — don't pollute sibling tests that may run after.
    saved = sys.modules.get("bpy")
    sys.modules["bpy"] = bpy_stub
    try:
        tag_redraw_all_areas(None)
    finally:
        if saved is not None:
            sys.modules["bpy"] = saved
        else:
            del sys.modules["bpy"]

    assert area.redraw_count == 1


def test_outer_exception_swallowed():
    """An exception reading wm.windows itself is caught by the outer guard."""
    class ExplodingWM:
        @property
        def windows(self):
            raise RuntimeError("wm gone")

    ctx = FakeContext(window_manager=ExplodingWM())
    # Must not raise.
    tag_redraw_all_areas(ctx)
