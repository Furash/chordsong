"""Panel visibility helpers for overlay operators.

Centralizes the "hide asset-shelf / HUD / T-panel / N-panel while an overlay
is up, restore when it closes" dance that used to be three near-identical
copies in operators/leader.py, operators/scripts_overlay.py, and
operators/recents.py. Also owns the Leader-to-child overlay panel-state
handoff (stash/take) — previously a module-level dict imported across
operator modules.

T/N regions are toggled through ``screen.region_toggle`` (what the N and T
keys run) so Blender's fade animation plays in every editor that supports
region overlap. Writing ``space.show_region_ui`` directly only animates
when the area is the context area, which is why split views and editors
other than the 3D View used to snap shut.

Fade caveat: while a fade-out runs, the region is still reported visible
(``show_region_ui`` reads True) until the blend timer ends, and toggling
again mid-fade leaves the region hidden. A restore that lands inside that
window — a chord typed faster than the fade — is therefore deferred with a
``bpy.app.timers`` retry until the region actually reads hidden, and only
then toggled back. ``hide_panels`` cancels any pending retry for the areas
it touches so an old restore can never pop a panel open under a new overlay.
"""

from ..core.contexts import SUPPORTED_SPACE_TYPES as _SUPPORTED_TYPES_WITH_PANELS

_ASSET_SHELF_ATTR = 'show_region_asset_shelf'
_HUD_ATTR = 'show_region_hud'
_N_PANEL_ATTR = 'show_region_ui'
_T_PANEL_ATTR = 'show_region_toolbar'

# show_region_* attribute -> region type for screen.region_toggle.
_REGION_TYPE_BY_ATTR = {
    _N_PANEL_ATTR: 'UI',
    _T_PANEL_ATTR: 'TOOLS',
}

# Deferred-restore retry cadence. Blender's region fade is a fraction of a
# second; six tries at 0.15 s cover it with margin, then we give up (the
# region never became hidden, so there is nothing to restore).
_RESTORE_RETRY_INTERVAL = 0.15
_RESTORE_RETRY_MAX = 6

# (area_ptr, attr) -> generation. A deferred restore only acts while its
# generation is current; hide_panels bumps the generation to cancel it.
_DEFERRED_RESTORES: dict = {}


def _find_window_region(area):
    try:
        for region in area.regions:
            if region.type == 'WINDOW':
                return region
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return None


def toggle_region(context, window, area, space, attr, target):
    """Flip a T/N region the way the N and T keys do.

    Runs ``screen.region_toggle`` under a temp_override for ``area`` so the
    native behaviour applies everywhere: animated where the editor supports
    region overlap, instant where Blender itself is instant. Falls back to
    writing the attribute (``target``) when the operator cannot run.
    Returns True when a change was issued.
    """
    region_type = _REGION_TYPE_BY_ATTR.get(attr)
    if region_type and context is not None and area is not None:
        try:
            import bpy  # type: ignore
            override = {"area": area}
            if window is not None:
                override["window"] = window
            win_region = _find_window_region(area)
            if win_region is not None:
                override["region"] = win_region
            with context.temp_override(**override):
                if bpy.ops.screen.region_toggle.poll():
                    result = bpy.ops.screen.region_toggle(region_type=region_type)
                    if 'FINISHED' in result:
                        return True
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    try:
        setattr(space, attr, target)
        return True
    except Exception:  # pylint: disable=broad-exception-caught
        return False


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


def _find_area(context, area_ptr, space_type):
    """Locate a live (window, area, active space) by area pointer and type,
    or (None, None, None) when it no longer exists."""
    try:
        for window in context.window_manager.windows:
            screen = window.screen
            if not screen:
                continue
            for area in screen.areas:
                if not _is_area_valid(area):
                    continue
                try:
                    if area.as_pointer() != area_ptr or area.type != space_type:
                        continue
                    space = area.spaces[0] if area.spaces else None
                    return window, area, space
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return None, None, None


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


def _cancel_deferred_restore(area_ptr, attr):
    key = (area_ptr, attr)
    _DEFERRED_RESTORES[key] = _DEFERRED_RESTORES.get(key, 0) + 1


def _schedule_deferred_restore(area_ptr, space_type, attr):
    """Re-show a T/N region once its fade-out has completed.

    Called when a restore arrives while the region still reads visible
    (fade pending). Polls via bpy.app.timers; toggles as soon as the region
    reads hidden; gives up after _RESTORE_RETRY_MAX tries or when a newer
    hide_panels call has cancelled this generation. The closure captures
    only plain data (no operator ``self``) — see tests/test_timer_closures.
    """
    key = (area_ptr, attr)
    generation = _DEFERRED_RESTORES.get(key, 0) + 1
    _DEFERRED_RESTORES[key] = generation
    tries = {"n": 0}

    def _retry():
        if _DEFERRED_RESTORES.get(key) != generation:
            return None  # superseded by a newer hide/restore
        tries["n"] += 1
        try:
            import bpy  # type: ignore
            window, area, space = _find_area(bpy.context, area_ptr, space_type)
            if space is None or not hasattr(space, attr):
                _DEFERRED_RESTORES.pop(key, None)
                return None
            if getattr(space, attr) is False:
                toggle_region(bpy.context, window, area, space, attr, True)
                _DEFERRED_RESTORES.pop(key, None)
                return None
        except Exception:  # pylint: disable=broad-exception-caught
            _DEFERRED_RESTORES.pop(key, None)
            return None
        if tries["n"] >= _RESTORE_RETRY_MAX:
            _DEFERRED_RESTORES.pop(key, None)
            return None
        return _RESTORE_RETRY_INTERVAL

    try:
        import bpy  # type: ignore
        bpy.app.timers.register(_retry, first_interval=_RESTORE_RETRY_INTERVAL)
    except Exception:  # pylint: disable=broad-exception-caught
        _DEFERRED_RESTORES.pop(key, None)


def hide_panels(context, hide_tn):
    """Hide panels for an overlay session and return a dict that
    `restore_panels` can replay.

    Always hides (when present):
      - Asset shelf (3D View sculpt/paint modes, node editors) — overlaps
        the bottom of the overlay
      - HUD / Redo floating region — occludes overlay

    Conditionally hides (when ``hide_tn`` is True):
      - N panel (sidebar)
      - T panel (toolshelf)

    Only the area the overlay was invoked in is touched. Overlays draw in
    that one area, so hiding panels in other areas of the same editor type
    (Dope Sheet + Timeline, split 3D Views) only disturbed the user. When
    the invoking area cannot be identified, nothing is hidden.

    Returned dict is keyed by area pointer and carries `space_type` so
    restoration can match the correct space even if Blender reorders areas.
    """
    panel_states = {}
    invoke_space = context.space_data
    invoke_space_type = invoke_space.type if invoke_space else 'VIEW_3D'
    try:
        invoke_area_ptr = context.area.as_pointer() if context.area else None
    except Exception:  # pylint: disable=broad-exception-caught
        invoke_area_ptr = None
    if invoke_area_ptr is None:
        return panel_states

    for window in context.window_manager.windows:
        try:
            screen = window.screen
            if not screen:
                continue
            for area in screen.areas:
                if not _is_area_valid(area):
                    continue
                try:
                    if area.as_pointer() != invoke_area_ptr:
                        continue
                    if area.type != invoke_space_type:
                        continue
                    if area.type not in _SUPPORTED_TYPES_WITH_PANELS:
                        continue

                    # Active space is always spaces[0] per Blender docs;
                    # `area.spaces[1:]` is a memory stack of editors the user
                    # switched AWAY from. Use the active space directly so
                    # writes reach the visible editor.
                    space = area.spaces[0] if area.spaces else None
                    if space is None:
                        print(
                            f"Chord Song: hide_panels skipped {area.type} area "
                            f"{area.as_pointer():#x} — area.spaces was empty."
                        )
                        continue

                    area_ptr = area.as_pointer()
                    state = {}

                    if hasattr(space, _ASSET_SHELF_ATTR):
                        state['asset_shelf'] = space.show_region_asset_shelf
                        if space.show_region_asset_shelf:
                            space.show_region_asset_shelf = False

                    if hasattr(space, _HUD_ATTR):
                        state['hud'] = space.show_region_hud
                        if space.show_region_hud:
                            space.show_region_hud = False

                    for key, attr in (('n_panel', _N_PANEL_ATTR), ('t_panel', _T_PANEL_ATTR)):
                        if not (hide_tn and hasattr(space, attr)):
                            continue
                        # A restore from a previous (fast) session may still be
                        # waiting for that fade to finish — cancel it so it
                        # cannot re-open the panel under this overlay.
                        _cancel_deferred_restore(area_ptr, attr)
                        visible = getattr(space, attr)
                        state[key] = visible
                        if visible:
                            toggle_region(context, window, area, space, attr, False)

                    if state:
                        state['space_type'] = invoke_space_type
                        panel_states[area_ptr] = state
                        # Force a redraw of this area — in rare races the
                        # show_region_* write doesn't propagate to the visible
                        # region until an unrelated event fires.
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
                    # T/N: re-show exactly the regions we hid (those that were
                    # visible). If the fade-out is still running the region
                    # reads visible; toggling now would leave it hidden, so
                    # defer until it actually reads hidden.
                    for key, attr in (('n_panel', _N_PANEL_ATTR), ('t_panel', _T_PANEL_ATTR)):
                        if state.get(key) is not True or not hasattr(space, attr):
                            continue
                        if getattr(space, attr) is False:
                            toggle_region(context, window, area, space, attr, True)
                        else:
                            _schedule_deferred_restore(area_ptr, space_type, attr)
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
