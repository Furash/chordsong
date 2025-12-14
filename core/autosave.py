import os
from dataclasses import dataclass
from typing import Any

from .config_io import dump_prefs

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

# Debounced autosave: schedule a single write after N seconds since the last change.
_DEFAULT_DELAY_S = 3.0


@dataclass
class _AutosaveState:
    """Module state for debounced autosave."""
    pending_prefs: Any = None
    pending_delay_s: float = _DEFAULT_DELAY_S


_state = _AutosaveState()


def autosave_path(config_path: str) -> str:
    """
    Given a config path ".../chordsong.json", returns ".../chordsong.autosave.json".
    If config_path is empty, returns "".
    """
    if not (config_path or "").strip():
        return ""
    base, ext = os.path.splitext(config_path)
    if not ext:
        return config_path + ".autosave"
    return base + ".autosave" + ext


def write_autosave(prefs) -> str:
    """
    Write an autosave file next to prefs.config_path.
    Returns the autosave filepath, or "" if skipped.
    """
    config_path = getattr(prefs, "config_path", "") or ""
    path = autosave_path(config_path)
    if not path:
        return ""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = dump_prefs(prefs)

    import json

    text = json.dumps(data, indent=2, ensure_ascii=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
        f.write("\n")

    return path


def _timer_cb():
    """
    Blender app timer callback. Runs once, writes autosave, then stops.
    """
    prefs = _state.pending_prefs
    _state.pending_prefs = None
    try:
        if not prefs:
            return None
        if getattr(prefs, "_chordsong_suspend_autosave", False):
            return None
        write_autosave(prefs)
    except Exception:
        # Best effort autosave; never crash Blender.
        return None
    return None


def schedule_autosave(prefs, delay_s: float | None = None):
    """
    Debounced autosave: schedules a single autosave write after delay_s seconds.
    If called again before the timer fires, it resets the timer.
    """
    try:
        import bpy  # type: ignore
    except Exception:
        return

    if delay_s is None:
        delay_s = _DEFAULT_DELAY_S
    _state.pending_delay_s = float(delay_s)
    _state.pending_prefs = prefs

    try:
        # Reset if already registered.
        if bpy.app.timers.is_registered(_timer_cb):
            bpy.app.timers.unregister(_timer_cb)
        bpy.app.timers.register(_timer_cb, first_interval=_state.pending_delay_s)
    except Exception:
        # If timers aren't available, do nothing.
        return


