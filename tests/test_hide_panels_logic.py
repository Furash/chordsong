"""Tests for hide_panels — area-type filtering + state-dict structure.

utils/panels.py top-imports bpy (via peer modules), so the production
helper cannot be imported directly. Mirror the body here against fake
bpy data classes. Update both sides together if production changes.

We cover:
  - Early-skip for area types not in _SUPPORTED_TYPES_WITH_PANELS.
  - Early-skip for areas whose type differs from the invoke space type.
  - State dict keyed by area.as_pointer(), carries 'space_type'.
  - Asset shelf and HUD are always hidden (when hide_tn is True OR False).
  - T-panel and N-panel only when hide_tn=True.
  - hide_tn=False leaves T/N alone.
  - Already-hidden panels have their state captured but aren't re-assigned
    (mirrors production; not separately testable beyond observing state).
"""
import os
import sys
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# --- mirrored from utils/panels.py -------------------------------------
_ASSET_SHELF_ATTR = 'show_region_asset_shelf'
_HUD_ATTR = 'show_region_hud'
_N_PANEL_ATTR = 'show_region_ui'
_T_PANEL_ATTR = 'show_region_toolbar'
_SUPPORTED_TYPES_WITH_PANELS = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}


def _is_area_valid(area):
    if not area:
        return False
    try:
        _ = area.spaces
        return True
    except Exception:
        return False


def hide_panels(context, hide_tn):
    panel_states = {}
    invoke_space = context.space_data
    invoke_space_type = invoke_space.type if invoke_space else 'VIEW_3D'

    for window in context.window_manager.windows:
        try:
            screen = window.screen
            if not screen:
                continue
            for area in screen.areas:
                if not _is_area_valid(area):
                    continue
                try:
                    if area.type != invoke_space_type:
                        continue
                    if area.type not in _SUPPORTED_TYPES_WITH_PANELS:
                        continue

                    space = None
                    for s in area.spaces:
                        if s.type == invoke_space_type:
                            space = s
                            break
                    if not space:
                        continue

                    state = {}

                    if area.type == 'VIEW_3D' and hasattr(space, _ASSET_SHELF_ATTR):
                        state['asset_shelf'] = space.show_region_asset_shelf
                        if space.show_region_asset_shelf:
                            space.show_region_asset_shelf = False

                    if hasattr(space, _HUD_ATTR):
                        state['hud'] = space.show_region_hud
                        if space.show_region_hud:
                            space.show_region_hud = False

                    if hide_tn and hasattr(space, _N_PANEL_ATTR):
                        state['n_panel'] = space.show_region_ui
                        if space.show_region_ui:
                            space.show_region_ui = False

                    if hide_tn and hasattr(space, _T_PANEL_ATTR):
                        state['t_panel'] = space.show_region_toolbar
                        if space.show_region_toolbar:
                            space.show_region_toolbar = False

                    if state:
                        state['space_type'] = invoke_space_type
                        panel_states[area.as_pointer()] = state
                except Exception:
                    continue
        except Exception:
            continue

    return panel_states
# -----------------------------------------------------------------------


# Fake bpy data classes --------------------------------------------------

class FakeSpace:
    def __init__(self, space_type='VIEW_3D', with_asset_shelf=True, with_hud=True,
                 with_n_panel=True, with_t_panel=True,
                 asset_shelf=True, hud=True, n_panel=True, t_panel=True):
        self.type = space_type
        if with_asset_shelf:
            self.show_region_asset_shelf = asset_shelf
        if with_hud:
            self.show_region_hud = hud
        if with_n_panel:
            self.show_region_ui = n_panel
        if with_t_panel:
            self.show_region_toolbar = t_panel


class FakeArea:
    def __init__(self, area_type='VIEW_3D', space=None, ptr=0x1000):
        self.type = area_type
        self.spaces = [space] if space is not None else [FakeSpace(area_type)]
        self._ptr = ptr

    def as_pointer(self):
        return self._ptr


@dataclass
class FakeScreen:
    areas: List[FakeArea] = field(default_factory=list)


@dataclass
class FakeWindow:
    screen: FakeScreen = None


@dataclass
class FakeWindowManager:
    windows: List[FakeWindow] = field(default_factory=list)


@dataclass
class FakeContext:
    window_manager: FakeWindowManager = field(default_factory=FakeWindowManager)
    space_data: object = None


def _ctx_with_areas(invoke_type, areas):
    screen = FakeScreen(areas=areas)
    wm = FakeWindowManager(windows=[FakeWindow(screen=screen)])
    return FakeContext(window_manager=wm, space_data=FakeSpace(invoke_type))


# Tests -----------------------------------------------------------------

def test_unsupported_area_type_skipped():
    # OUTLINER is not in _SUPPORTED_TYPES_WITH_PANELS; also its type won't
    # match invoke_space_type ('OUTLINER' here), which itself isn't
    # supported, so no state is captured.
    space = FakeSpace('OUTLINER', with_asset_shelf=False)
    area = FakeArea('OUTLINER', space=space, ptr=0xA)
    screen = FakeScreen(areas=[area])
    wm = FakeWindowManager(windows=[FakeWindow(screen=screen)])
    ctx = FakeContext(window_manager=wm, space_data=FakeSpace('OUTLINER', with_asset_shelf=False))
    result = hide_panels(ctx, hide_tn=True)
    assert result == {}


def test_area_type_mismatch_skipped():
    # Invoke space is VIEW_3D, but the only area is NODE_EDITOR — skipped.
    node_space = FakeSpace('NODE_EDITOR', with_asset_shelf=False)
    node_area = FakeArea('NODE_EDITOR', space=node_space, ptr=0xB)
    ctx = _ctx_with_areas('VIEW_3D', [node_area])
    result = hide_panels(ctx, hide_tn=True)
    assert result == {}


def test_view3d_hide_tn_true_captures_all_four():
    space = FakeSpace('VIEW_3D')
    area = FakeArea('VIEW_3D', space=space, ptr=0x1000)
    ctx = _ctx_with_areas('VIEW_3D', [area])
    result = hide_panels(ctx, hide_tn=True)

    assert 0x1000 in result
    state = result[0x1000]
    assert state['space_type'] == 'VIEW_3D'
    assert state['asset_shelf'] is True
    assert state['hud'] is True
    assert state['n_panel'] is True
    assert state['t_panel'] is True
    # All four got toggled off on the fake space.
    assert space.show_region_asset_shelf is False
    assert space.show_region_hud is False
    assert space.show_region_ui is False
    assert space.show_region_toolbar is False


def test_view3d_hide_tn_false_leaves_tn_alone():
    space = FakeSpace('VIEW_3D')
    area = FakeArea('VIEW_3D', space=space, ptr=0x1000)
    ctx = _ctx_with_areas('VIEW_3D', [area])
    result = hide_panels(ctx, hide_tn=False)

    state = result[0x1000]
    assert 'asset_shelf' in state
    assert 'hud' in state
    assert 'n_panel' not in state
    assert 't_panel' not in state
    # T/N panels remain visible.
    assert space.show_region_ui is True
    assert space.show_region_toolbar is True
    # Asset shelf and HUD are hidden.
    assert space.show_region_asset_shelf is False
    assert space.show_region_hud is False


def test_node_editor_skips_asset_shelf_key():
    # Asset shelf state is only captured for VIEW_3D (production gates on
    # `area.type == 'VIEW_3D'`). NODE_EDITOR gets HUD + T/N only.
    space = FakeSpace('NODE_EDITOR')
    area = FakeArea('NODE_EDITOR', space=space, ptr=0x2000)
    ctx = _ctx_with_areas('NODE_EDITOR', [area])
    result = hide_panels(ctx, hide_tn=True)

    state = result[0x2000]
    assert state['space_type'] == 'NODE_EDITOR'
    assert 'asset_shelf' not in state
    assert 'hud' in state
    assert 'n_panel' in state
    assert 't_panel' in state


def test_state_keyed_by_area_pointer():
    s1 = FakeSpace('VIEW_3D')
    s2 = FakeSpace('VIEW_3D')
    a1 = FakeArea('VIEW_3D', space=s1, ptr=0xAAAA)
    a2 = FakeArea('VIEW_3D', space=s2, ptr=0xBBBB)
    ctx = _ctx_with_areas('VIEW_3D', [a1, a2])
    result = hide_panels(ctx, hide_tn=True)
    assert set(result.keys()) == {0xAAAA, 0xBBBB}


def test_space_without_panel_attrs_captures_nothing():
    # A space with no relevant attrs produces an empty state — which means
    # the area is not even inserted into panel_states (the `if state:` guard).
    space = FakeSpace('VIEW_3D',
                      with_asset_shelf=False, with_hud=False,
                      with_n_panel=False, with_t_panel=False)
    area = FakeArea('VIEW_3D', space=space, ptr=0xCCCC)
    ctx = _ctx_with_areas('VIEW_3D', [area])
    result = hide_panels(ctx, hide_tn=True)
    assert result == {}


def test_already_hidden_panel_still_captured_as_false():
    # If a panel is already hidden, state captures False and production
    # must NOT re-assign (production guards the set with `if ...:`).
    space = FakeSpace('VIEW_3D', asset_shelf=False, hud=True, n_panel=False, t_panel=True)
    area = FakeArea('VIEW_3D', space=space, ptr=0xDDDD)
    ctx = _ctx_with_areas('VIEW_3D', [area])
    result = hide_panels(ctx, hide_tn=True)

    state = result[0xDDDD]
    assert state['asset_shelf'] is False
    assert state['hud'] is True
    assert state['n_panel'] is False
    assert state['t_panel'] is True
    # After hide: asset_shelf stays False, hud flips to False, n_panel stays
    # False, t_panel flips to False.
    assert space.show_region_asset_shelf is False
    assert space.show_region_hud is False
    assert space.show_region_ui is False
    assert space.show_region_toolbar is False


def test_no_space_data_defaults_to_view3d():
    # context.space_data is None → invoke_space_type defaults to VIEW_3D.
    space = FakeSpace('VIEW_3D')
    area = FakeArea('VIEW_3D', space=space, ptr=0xEEEE)
    screen = FakeScreen(areas=[area])
    wm = FakeWindowManager(windows=[FakeWindow(screen=screen)])
    ctx = FakeContext(window_manager=wm, space_data=None)
    result = hide_panels(ctx, hide_tn=True)
    assert 0xEEEE in result
    assert result[0xEEEE]['space_type'] == 'VIEW_3D'


def test_invalid_area_skipped():
    class InvalidArea:
        # Accessing .spaces raises → _is_area_valid returns False.
        type = 'VIEW_3D'
        @property
        def spaces(self):
            raise ReferenceError("area freed")
        def as_pointer(self):
            return 0xDEAD

    ok_space = FakeSpace('VIEW_3D')
    ok_area = FakeArea('VIEW_3D', space=ok_space, ptr=0xBEEF)
    screen = FakeScreen(areas=[InvalidArea(), ok_area])
    wm = FakeWindowManager(windows=[FakeWindow(screen=screen)])
    ctx = FakeContext(window_manager=wm, space_data=FakeSpace('VIEW_3D'))

    result = hide_panels(ctx, hide_tn=True)
    assert 0xDEAD not in result
    assert 0xBEEF in result
