"""Statistics manager for tracking operator and chord usage."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json
import os
from datetime import datetime, timezone
from typing import Dict, Optional
import bpy


class ChordSong_StatsManager:
    """
    Singleton-style statistics manager that tracks operator and chord usage.
    Uses an in-memory buffer and periodic writes to disk to avoid blocking the main thread.
    """
    
    # Constants
    DEFAULT_INTERVAL = 180.0
    DISABLED_CHECK_INTERVAL = 60.0
    STATS_FILENAME = "chordsong_stats.json"
    _CATEGORIES = ("operators", "chords")

    # Class state
    _buffer: Dict[str, Dict[str, int]] = {"operators": {}, "chords": {}}
    _file_cache: Optional[Dict[str, Dict[str, int]]] = None  # loaded at startup, refreshed after save
    _dirty: bool = False
    _cached_internal_path: Optional[str] = None
    timer_should_stop: bool = False  # Public flag for preference callback coordination
    
    @classmethod
    def _get_addon_package(cls) -> str:
        """Get the root addon package name (cached via import)."""
        from ..utils.addon_package import addon_root_package
        return addon_root_package(__package__)
    
    @classmethod
    def _get_preferences(cls):
        """Get addon preferences. Returns None if unavailable."""
        try:
            pkg = cls._get_addon_package()
            if pkg in bpy.context.preferences.addons:
                return bpy.context.preferences.addons[pkg].preferences
        except (AttributeError, KeyError):
            pass
        return None
    
    @classmethod
    def get_internal_file_path(cls) -> str:
        """
        Get the path to the internal statistics JSON file.
        
        Returns:
            Path to internal stats file, or empty string if unavailable.
        """
        if cls._cached_internal_path:
            return cls._cached_internal_path
        try:
            pkg = cls._get_addon_package()
            extension_dir = bpy.utils.extension_path_user(pkg, path="", create=True)
            if extension_dir:
                cls._cached_internal_path = os.path.join(extension_dir, cls.STATS_FILENAME)
                return cls._cached_internal_path
        except Exception:
            pass
        return ""
    
    @classmethod
    def _get_export_path(cls) -> Optional[str]:
        """Get user-configured export path with .json extension enforced."""
        prefs = cls._get_preferences()
        if not prefs:
            return None
        
        export_path = getattr(prefs, 'stats_export_path', '').strip()
        if not export_path:
            return None
        
        # Ensure .json extension
        if not export_path.lower().endswith('.json'):
            export_path += '.json'
        
        return export_path

    @classmethod
    def get_stats_file_path(cls) -> str:
        """
        Get the canonical stats file path: export path if set, else internal path.
        Used for load at startup, Export, auto-save, and Reload so one file is the source of truth.
        """
        export_path = cls._get_export_path()
        if export_path:
            return export_path
        return cls.get_internal_file_path() or ""
    
    @classmethod
    def record(cls, category: str, identifier: str) -> None:
        """
        Record a statistics event to the internal buffer.
        
        Args:
            category: Category of the event ('operators', 'chords')
            identifier: String identifier for the event
        """
        if category not in cls._buffer:
            return
        
        cls._buffer[category][identifier] = cls._buffer[category].get(identifier, 0) + 1
        cls._dirty = True
        # Do not schedule UI refresh from here: modifying prefs.stats_collection from a timer
        # can cause Blender crashes. User can click Refresh or re-open the Stats tab to update.
    
    @classmethod
    def mark_dirty(cls) -> None:
        """Mark statistics as dirty to trigger a save on next timer cycle."""
        cls._dirty = True
    
    
    @classmethod
    def _normalize_count(cls, value) -> int:
        """Return count as int; supports legacy dict format {"count": n}."""
        if isinstance(value, dict):
            return value.get("count", 0)
        return int(value) if isinstance(value, (int, float)) else 0

    @classmethod
    def _ensure_json_path(cls, path: str) -> str:
        """Strip path and append .json if missing. Caller should check path non-empty and file exists if needed."""
        path = (path or "").strip()
        if path and not path.lower().endswith(".json"):
            path = path + ".json"
        return path

    @classmethod
    def _data_to_cache(cls, data: Dict) -> Dict[str, Dict[str, int]]:
        """Build {operators: {...}, chords: {...}} from loaded JSON data, with normalized counts."""
        cache = {}
        for category in cls._CATEGORIES:
            if category in data and isinstance(data[category], dict):
                cache[category] = {
                    k: cls._normalize_count(v)
                    for k, v in data[category].items()
                }
            else:
                cache[category] = {}
        return cache

    @classmethod
    def _load_data_from_file(cls, path: str) -> Dict:
        """Load statistics data from JSON file."""
        if not os.path.exists(path):
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure metadata structure exists
                if "_metadata" not in data:
                    data["_metadata"] = {}
                if "last_saved" not in data["_metadata"]:
                    data["_metadata"]["last_saved"] = ""
                if "blacklist" not in data["_metadata"]:
                    data["_metadata"]["blacklist"] = []
                return data
        except (json.JSONDecodeError, IOError):
            return {"_metadata": {"last_saved": "", "blacklist": []}}

    @classmethod
    def load_from_file(cls) -> None:
        """
        Load statistics from the stats file into the in-memory cache.
        Called at addon startup; uses export path if set, else internal path.
        Replaces current Blender data with file content.
        """
        path = cls.get_stats_file_path()
        if not path or not os.path.exists(path):
            return
        try:
            data = cls._load_data_from_file(path)
            cls._file_cache = cls._data_to_cache(data)
            cls._buffer = {"operators": {}, "chords": {}}
            cls._dirty = False
        except Exception:
            cls._file_cache = None

    @classmethod
    def reload_from_path(cls, path: str) -> bool:
        """
        Reload statistics from a JSON file path (canonical stats file or any path).
        Replaces in-memory cache and buffer with file contents.
        Returns True if file was loaded, False if path empty, file missing, or error.
        """
        path = cls._ensure_json_path(path)
        if not path or not os.path.exists(path):
            return False
        try:
            data = cls._load_data_from_file(path)
            cls._file_cache = cls._data_to_cache(data)
            cls._buffer = {"operators": {}, "chords": {}}
            cls._dirty = False
            return True
        except Exception:
            return False

    @classmethod
    def write_current_to_file(cls, path: str) -> bool:
        """
        Overwrite the stats file with current UI state (file cache + buffer).
        On success, clears the buffer so in-memory state matches the file.
        Returns True on success, False otherwise.
        """
        path = cls._ensure_json_path(path)
        if not path:
            return False
        try:
            data = {cat: dict(cls.get_stats(cat)) for cat in cls._CATEGORIES}
            data["_metadata"] = {}
            success = cls._write_json_file(path, data, sort_keys=True)
            if success:
                cls._file_cache = {cat: dict(data[cat]) for cat in cls._CATEGORIES}
                cls._buffer = {"operators": {}, "chords": {}}
                cls._dirty = False
            return success
        except Exception:
            return False

    @classmethod
    def _write_json_file(cls, path: str, data: Dict, sort_keys: bool = False) -> bool:
        """
        Write data to JSON file with timestamp and blacklist.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            # Ensure metadata exists and update timestamp (human-readable ISO 8601)
            if "_metadata" not in data:
                data["_metadata"] = {}
            data["_metadata"]["last_saved"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Sync blacklist from preferences to metadata
            prefs = cls._get_preferences()
            if prefs:
                try:
                    blacklist_json = getattr(prefs, 'stats_blacklist', '[]')
                    blacklist_list = json.loads(blacklist_json)
                    data["_metadata"]["blacklist"] = blacklist_list
                except Exception:
                    # If blacklist can't be read, keep existing or use empty list
                    if "blacklist" not in data["_metadata"]:
                        data["_metadata"]["blacklist"] = []
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, sort_keys=sort_keys)
            
            return True
        except (IOError, OSError):
            return False
    
    @classmethod
    def save_to_disk(cls) -> Optional[float]:
        """
        Periodic task: overwrite the stats file with current UI state (what get_stats() returns).
        Uses the same file as Export and load (get_stats_file_path()).
        """
        if cls.timer_should_stop:
            cls.timer_should_stop = False
            return None
        prefs = cls._get_preferences()
        interval = cls.DEFAULT_INTERVAL
        if prefs:
            interval = float(getattr(prefs, "stats_auto_export_interval", cls.DEFAULT_INTERVAL))
            if interval <= 0:
                return cls.DISABLED_CHECK_INTERVAL
        if not cls._dirty:
            return interval
        path = cls.get_stats_file_path()
        if not path:
            return interval
        cls.write_current_to_file(path)
        return interval
    
    @classmethod
    def clear_all(cls) -> None:
        """Reset all statistics (buffer, file cache, and stats file)."""
        cls._buffer = {"operators": {}, "chords": {}}
        cls._file_cache = {"operators": {}, "chords": {}}
        cls._dirty = False
        path = cls.get_stats_file_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    
    @classmethod
    def get_stats(cls, category: str) -> Dict[str, int]:
        """
        Return stats for a category: file cache + buffer (what the UI displays).
        category: 'operators' or 'chords'. Returns dict of identifier -> count.
        """
        result = {}
        if cls._file_cache is not None and category in cls._file_cache:
            result = dict(cls._file_cache[category])
        else:
            path = cls.get_stats_file_path()
            if path:
                data = cls._load_data_from_file(path)
                if category in data and category != "_metadata":
                    for identifier, value in data[category].items():
                        result[identifier] = cls._normalize_count(value)
        # Add unsaved buffer so UI never shows less than file
        if category in cls._buffer:
            for identifier, value in cls._buffer[category].items():
                count = cls._normalize_count(value)
                existing = cls._normalize_count(result.get(identifier, 0))
                result[identifier] = existing + count
        
        return result
    
    @classmethod
    def load_blacklist_from_file(cls) -> None:
        """
        Load blacklist from the stats file and sync to preferences.
        Called on addon registration; uses same file as load_from_file (get_stats_file_path).
        """
        cls.load_blacklist_from_path(cls.get_stats_file_path())

    @classmethod
    def load_blacklist_from_path(cls, path: str) -> None:
        """
        Load blacklist from a statistics JSON file and sync to preferences.
        Used after reload_from_path so the UI filter matches the loaded file.
        """
        prefs = cls._get_preferences()
        if not prefs:
            return
        path = cls._ensure_json_path(path or "")
        if not path or not os.path.exists(path):
            return
        try:
            data = cls._load_data_from_file(path)
            blacklist = data.get("_metadata", {}).get("blacklist", [])
            if blacklist:
                try:
                    current_blacklist_json = getattr(prefs, "stats_blacklist", "[]") or "[]"
                    current_blacklist = json.loads(current_blacklist_json)
                    if len(blacklist) >= len(current_blacklist):
                        prefs.stats_blacklist = json.dumps(sorted(blacklist))
                except Exception:
                    pass
        except Exception:
            pass
