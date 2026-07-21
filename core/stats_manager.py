"""Statistics manager: captures operator usage from ``wm.reports`` and
chord usage from the leader operator, buffers counts in memory, and
periodically persists them to a JSON file.

Operator capture relies on the ``window_manager.reports`` RNA collection
(Blender 5.2+): every Info-logged operator run produces one report with a
session-unique, monotonically increasing ``session_uid``. A 1s timer walks
the collection tail backwards to the last seen uid, so each run is counted
exactly once — no polling of ``wm.operators`` / ``modal_operators`` needed.
On older Blender versions operator capture is silently unavailable; chord
capture still works.
"""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import os
import time
from datetime import datetime, timezone

import bpy

from . import stats_store
from ..utils.addon_package import addon_root_package

STATS_FILENAME = "chordsong_stats.json"
POLL_INTERVAL = 1.0
IDLE_INTERVAL = 5.0  # tick rate while stats are disabled
DEFAULT_SAVE_INTERVAL = 180.0

def _empty_counts() -> dict:
    return {category: {} for category in stats_store.CATEGORIES}


_buffer = _empty_counts()
_file_cache = None  # counts loaded from disk; None until first load
_dirty = False
_last_uid = 0
_uid_initialized = False
_last_save = 0.0
_cached_internal_path = None
_property_values = {}  # path -> last seen value string (for convert prefill)

# Operator runs triggered by chordsong itself (chord mappings, recents
# replay). Those are already counted as chord usage, so the next matching
# wm.reports entry is skipped instead of double-counted as raw operator use.
_expected_ops = {}  # idname -> list of monotonic expiry deadlines
EXPECT_TTL = 60.0  # generous: modal ops (e.g. transform) report on confirm


def _prefs():
    try:
        pkg = addon_root_package(__package__)
        addons = bpy.context.preferences.addons
        if pkg in addons:
            return addons[pkg].preferences
    except (AttributeError, KeyError):
        pass
    return None


def stats_supported() -> bool:
    """Statistics module requires Blender 5.2+ (wm.reports with session_uid)."""
    return bpy.app.version >= (5, 2, 0)


def reports_available() -> bool:
    """True when this Blender exposes the wm.reports RNA collection (5.2+)."""
    try:
        return "reports" in bpy.types.WindowManager.bl_rna.properties
    except Exception:
        return False


# -- File paths --


def get_internal_file_path() -> str:
    global _cached_internal_path
    if _cached_internal_path:
        return _cached_internal_path
    try:
        pkg = addon_root_package(__package__)
        extension_dir = bpy.utils.extension_path_user(pkg, path="", create=True)
        if extension_dir:
            _cached_internal_path = os.path.join(extension_dir, STATS_FILENAME)
            return _cached_internal_path
    except Exception:
        pass
    return ""


def get_stats_file_path() -> str:
    """Canonical stats file: user export path if set, else internal path."""
    prefs = _prefs()
    path = (getattr(prefs, "stats_export_path", "") or "").strip() if prefs else ""
    if path:
        if not path.lower().endswith(".json"):
            path += ".json"
        return path
    return get_internal_file_path()


# -- Recording --


def record(category: str, identifier: str) -> None:
    global _dirty
    if category not in _buffer or not identifier:
        return
    _buffer[category][identifier] = _buffer[category].get(identifier, 0) + 1
    _dirty = True


def _tracking_active() -> bool:
    if not stats_supported():
        return False
    prefs = _prefs()
    return bool(prefs and getattr(prefs, "enable_stats", False))


def record_chord(chord_tokens) -> None:
    """Record a chord execution; no-op while stats are disabled or unsupported."""
    if not _tracking_active():
        return
    record("chords", " ".join(chord_tokens))


def record_script(filepath: str) -> None:
    """Record a user-script execution (keyed by file name); no-op while disabled."""
    if not _tracking_active():
        return
    record("scripts", os.path.basename((filepath or "").strip()))


def expect_operator_report(idname: str) -> None:
    """Mark the next wm.reports entry for this operator as chordsong-triggered.

    Called right after chordsong invokes an operator; the poll consumes one
    matching report without counting it. If the operator never reports
    (CANCELLED, no REGISTER flag), the expectation silently expires.
    """
    if not _tracking_active():
        return
    idname = (idname or "").strip()
    if idname:
        _expected_ops.setdefault(idname, []).append(time.monotonic() + EXPECT_TTL)


def _consume_expected(idname: str) -> bool:
    """Pop one live expectation for idname; True when the report should be skipped."""
    deadlines = _expected_ops.get(idname)
    if not deadlines:
        return False
    now = time.monotonic()
    live = [d for d in deadlines if d > now]
    consumed = bool(live)
    if consumed:
        live.pop(0)
    if live:
        _expected_ops[idname] = live
    else:
        _expected_ops.pop(idname, None)
    return consumed


def mark_dirty() -> None:
    global _dirty
    _dirty = True


def get_stats(category: str) -> dict:
    """Counts for a category: file cache + unsaved buffer (what the UI shows)."""
    global _file_cache
    if _file_cache is None:
        load_from_file()
    result = dict(_file_cache.get(category, {})) if _file_cache else {}
    for name, count in _buffer.get(category, {}).items():
        result[name] = result.get(name, 0) + count
    return result


# -- Report polling --


def _poll_reports() -> None:
    """Count operator runs reported since the last poll (uid watermark)."""
    global _last_uid, _uid_initialized
    wm = getattr(bpy.context, "window_manager", None)
    reports = getattr(wm, "reports", None)
    if reports is None:
        return

    if not _uid_initialized:
        # Skip anything logged before stats tracking started (or before an
        # addon reload) so history is never double-counted.
        _uid_initialized = True
        if len(reports) > 0:
            _last_uid = reports[len(reports) - 1].session_uid
        return

    fresh = []
    for i in range(len(reports) - 1, -1, -1):
        r = reports[i]
        if r.session_uid <= _last_uid:
            break
        fresh.append(r)
    if not fresh:
        return

    _last_uid = fresh[0].session_uid
    for r in reversed(fresh):
        if r.type == 'OPERATOR':
            idname = stats_store.parse_operator_report(r.message)
            if idname and not _consume_expected(idname):
                record("operators", idname)
        elif r.type == 'PROPERTY':
            parsed = stats_store.parse_property_report(r.message)
            if parsed:
                path, value = parsed
                record("properties", path)
                _property_values[path] = value


# -- Persistence --


def _load_data(path: str) -> dict:
    import json

    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return {}


def _load_property_values(data: dict) -> None:
    """Sync last-seen property values from a stats file's metadata."""
    global _property_values
    raw = data.get("_metadata", {}).get("property_values", {})
    if isinstance(raw, dict):
        _property_values = {str(k): str(v) for k, v in raw.items()}


def get_last_property_value(path: str) -> str:
    """Last value seen for a tracked property path ("" when unknown)."""
    return _property_values.get(path, "")


def load_from_file() -> None:
    """Load counts from the canonical stats file into the cache."""
    global _file_cache, _buffer, _dirty
    data = _load_data(get_stats_file_path())
    _file_cache = stats_store.data_to_counts(data)
    _load_property_values(data)
    _buffer = _empty_counts()
    _dirty = False


def reload_from_path(path: str) -> bool:
    """Replace in-memory counts with the contents of an arbitrary JSON file."""
    global _file_cache, _buffer, _dirty
    path = (path or "").strip()
    if path and not path.lower().endswith(".json"):
        path += ".json"
    if not path or not os.path.exists(path):
        return False
    data = _load_data(path)
    _file_cache = stats_store.data_to_counts(data)
    _load_property_values(data)
    _buffer = _empty_counts()
    _dirty = False
    load_blacklist_from_path(path)
    return True


def write_current_to_file(path: str = "") -> bool:
    """Persist the merged counts (cache + buffer) to the stats file."""
    global _file_cache, _buffer, _dirty, _last_save
    import json

    path = (path or "").strip() or get_stats_file_path()
    if not path:
        return False
    if not path.lower().endswith(".json"):
        path += ".json"

    counts = {cat: get_stats(cat) for cat in stats_store.CATEGORIES}
    prefs = _prefs()
    blacklist = stats_store.parse_blacklist(
        getattr(prefs, "stats_blacklist", "[]") if prefs else "[]"
    )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    data = stats_store.counts_to_data(
        counts, blacklist=blacklist, last_saved=stamp,
        property_values=_property_values,
    )

    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, sort_keys=True)
    except OSError:
        return False

    _file_cache = counts
    _buffer = _empty_counts()
    _dirty = False
    _last_save = time.monotonic()
    return True


def clear_all() -> None:
    """Reset all statistics (memory and file)."""
    global _buffer, _file_cache, _dirty, _property_values
    _buffer = _empty_counts()
    _file_cache = _empty_counts()
    _property_values = {}
    _dirty = False
    path = get_stats_file_path()
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def load_blacklist_from_path(path: str) -> None:
    """Sync the blacklist stored in a stats file into preferences."""
    prefs = _prefs()
    if not prefs:
        return
    data = _load_data(path)
    blacklist = data.get("_metadata", {}).get("blacklist", [])
    if isinstance(blacklist, list) and blacklist:
        prefs.stats_blacklist = stats_store.dump_blacklist({str(b) for b in blacklist})


# -- Timer --


def _tick():
    prefs = _prefs()
    if prefs is None or not getattr(prefs, "enable_stats", False):
        return IDLE_INTERVAL
    try:
        _poll_reports()
    except Exception:
        pass
    try:
        interval = float(getattr(prefs, "stats_auto_export_interval", DEFAULT_SAVE_INTERVAL) or 0)
        if interval > 0 and _dirty and (time.monotonic() - _last_save) >= interval:
            write_current_to_file()
    except Exception:
        pass
    return POLL_INTERVAL


def register_timer() -> None:
    global _uid_initialized, _last_save
    if not stats_supported():
        return
    _uid_initialized = False
    _last_save = time.monotonic()
    if not bpy.app.timers.is_registered(_tick):
        bpy.app.timers.register(_tick, first_interval=POLL_INTERVAL, persistent=True)


def unregister_timer() -> None:
    """Stop the timer, flushing unsaved counts first."""
    try:
        if _dirty:
            write_current_to_file()
    except Exception:
        pass
    try:
        if bpy.app.timers.is_registered(_tick):
            bpy.app.timers.unregister(_tick)
    except Exception:
        pass
