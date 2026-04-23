"""Panel visibility helpers for overlay operators.

Centralizes the "hide asset-shelf / HUD / T-panel / N-panel while an overlay
is up, restore when it closes" dance that used to be three near-identical
copies in operators/leader.py, operators/scripts_overlay.py, and
operators/recents.py. Also owns the Leader-to-child overlay panel-state
handoff (stash/take) — previously a module-level dict imported across
operator modules.
"""

_ASSET_SHELF_ATTR = 'show_region_asset_shelf'
_HUD_ATTR = 'show_region_hud'
_N_PANEL_ATTR = 'show_region_ui'
_T_PANEL_ATTR = 'show_region_toolbar'

# Editor types that have collapsible T/N panels. Other areas (Outliner,
# Properties, etc.) are skipped during hide/restore.
_SUPPORTED_TYPES_WITH_PANELS = {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR', 'SEQUENCE_EDITOR'}


def _is_area_valid(area):
    """True iff `area` is a live bpy area (best-effort — spaces access is
    the safest probe; accessing `.type` on a partially-destroyed area can
    crash Blender at the C level)."""
    if not area:
        return False
    try:
        _ = area.spaces
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def restore_panel_attr(space, panel_state, key, attr):
    """Restore a single panel attribute on `space` from `panel_state[key]`.

    No-op if the key is absent, the attribute doesn't exist on the space,
    or the current value already matches.
    """
    if key not in panel_state:
        return
    if not hasattr(space, attr):
        return
    target = panel_state[key]
    if getattr(space, attr) != target:
        setattr(space, attr, target)


def hide_panels(context, hide_tn):
    """Hide panels for an overlay session and return a dict that
    `restore_panels` can replay.

    Always hides (when present):
      - Asset shelf (3D View only) — overlaps bottom overlay
      - HUD / Redo floating region — occludes overlay

    Conditionally hides (when ``hide_tn`` is True):
      - N panel (sidebar)
      - T panel (toolshelf)

    Returned dict is keyed by area pointer and carries `space_type` so
    restoration can match the correct space even if Blender reorders areas.
    """
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

                    # Active space is always spaces[0] per Blender docs;
                    # `area.spaces[1:]` is a memory stack of editors the user
                    # switched AWAY from. The previous for-loop picked the
                    # first type-matching space — usually the active one, but
                    # after switching editors back and forth the list order
                    # could leave a stale same-type space at a non-zero index,
                    # and writes to it wouldn't affect the visible area. Use
                    # the active space directly.
                    space = area.spaces[0] if area.spaces else None
                    if space is None:
                        print(
                            f"Chord Song: hide_panels skipped {area.type} area "
                            f"{area.as_pointer():#x} — area.spaces was empty."
                        )
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
                        # Force a redraw of this area — in rare races the
                        # show_region_* write doesn't propagate to the visible
                        # region until an unrelated event fires. Explicit
                        # tag_redraw eliminates the "panels still visible
                        # briefly" symptom that users have reported as
                        # "won't hide until I recreate the workspace".
                        try:
                            area.tag_redraw()
                        except Exception:  # pylint: disable=broad-exception-caught
                            pass
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
        except Exception:  # pylint: disable=broad-exception-caught
            continue

    return panel_states


def restore_panels(context, panel_states):
    """Restore panels that `hide_panels` stashed. Safe to call with an
    empty dict; iterates live areas and replays each captured attr."""
    if not panel_states:
        return
    for window in context.window_manager.windows:
        try:
            screen = window.screen
            if not screen:
                continue
            for area in screen.areas:
                if not _is_area_valid(area):
                    continue
                try:
                    area_ptr = area.as_pointer()
                    if area_ptr not in panel_states:
                        continue
                    state = panel_states[area_ptr]
                    space_type = state.get('space_type', 'VIEW_3D')
                    if area.type != space_type:
                        continue
                    space = None
                    for s in area.spaces:
                        if s.type == space_type:
                            space = s
                            break
                    if not space:
                        continue
                    restore_panel_attr(space, state, 'asset_shelf', _ASSET_SHELF_ATTR)
                    restore_panel_attr(space, state, 'hud',         _HUD_ATTR)
                    restore_panel_attr(space, state, 'n_panel',     _N_PANEL_ATTR)
                    restore_panel_attr(space, state, 't_panel',     _T_PANEL_ATTR)
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
        except Exception:  # pylint: disable=broad-exception-caught
            continue


# ----------------------------------------------------------------------
# Inter-operator handoff
# ----------------------------------------------------------------------
# When Leader transitions into a child overlay (Recents or Scripts Overlay),
# the child owes the user a restoration when IT closes — otherwise panels
# would flash back visible mid-transition. Leader stashes its panel_states
# dict here; the child takes it on invoke.
#
# Previously the state lived as a module-level global inside
# operators/leader.py, imported across modules. Encapsulating in this
# module avoids the reach-across-packages coupling.

_PENDING_HANDOFF: dict = {}


def stash_panel_states(panel_states):
    """Queue a panel_states dict for pickup by the next overlay to invoke."""
    _PENDING_HANDOFF.clear()
    if panel_states:
        _PENDING_HANDOFF.update(panel_states)


def take_panel_states():
    """Atomically retrieve and clear any stashed panel_states. Returns {}
    when nothing is queued."""
    result = dict(_PENDING_HANDOFF)
    _PENDING_HANDOFF.clear()
    return result
