"""Statistics manager for tracking operator and chord usage."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json
import os
from typing import Dict, Optional
import bpy


class ChordSong_StatsManager:
    """
    Singleton-style statistics manager that tracks operator and chord usage.
    Uses an in-memory buffer and periodic writes to disk to ensure zero performance impact.
    """
    
    # Constants
    DEFAULT_INTERVAL = 180.0
    DISABLED_CHECK_INTERVAL = 60.0
    STATS_FILENAME = "chordsong_stats.json"
    
    # Class state
    _buffer: Dict[str, Dict[str, int]] = {"operators": {}, "chords": {}}
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
        
        if hasattr(bpy.utils, 'extension_path_user'):
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
        cls._schedule_ui_refresh()
    
    @classmethod
    def _schedule_ui_refresh(cls) -> None:
        """Schedule a debounced UI refresh if conditions are met."""
        prefs = cls._get_preferences()
        if not prefs:
            return
        
        should_refresh = (
            getattr(prefs, 'prefs_tab', None) == "STATS" and
            getattr(prefs, 'stats_realtime_refresh', False)
        )
        
        if should_refresh:
            try:
                bpy.app.timers.unregister(cls._debounced_refresh)
            except ValueError:
                pass
            bpy.app.timers.register(cls._debounced_refresh, first_interval=0.5)
    
    @classmethod
    def _debounced_refresh(cls):
        """Debounced refresh function called by timer."""
        prefs = cls._get_preferences()
        if prefs and getattr(prefs, 'prefs_tab', None) == "STATS":
            try:
                from ..operators.stats_operators import _refresh_stats_ui
                _refresh_stats_ui(prefs, export_to_file=False)
            except Exception:
                pass
        return None
    
    @classmethod
    def _normalize_count(cls, value) -> int:
        """Normalize count value (handles legacy dict format)."""
        if isinstance(value, dict):
            return value.get("count", 0)
        return int(value) if isinstance(value, (int, float)) else 0
    
    @classmethod
    def _load_data_from_file(cls, path: str) -> Dict:
        """Load statistics data from JSON file."""
        if not os.path.exists(path):
            return {}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    @classmethod
    def _merge_buffer_into_data(cls, data: Dict, buffer: Dict) -> None:
        """Merge buffer counts into data dictionary (in-place)."""
        for category, items in buffer.items():
            if category not in data:
                data[category] = {}
            
            for identifier, buffer_count in items.items():
                buffer_count = cls._normalize_count(buffer_count)
                existing_count = cls._normalize_count(data[category].get(identifier, 0))
                data[category][identifier] = existing_count + buffer_count
    
    @classmethod
    def _write_json_file(cls, path: str, data: Dict, sort_keys: bool = False) -> bool:
        """
        Write data to JSON file.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, sort_keys=sort_keys)
            
            return True
        except (IOError, OSError):
            return False
    
    @classmethod
    def _restore_buffer(cls, failed_buffer: Dict) -> None:
        """Restore failed buffer back into active buffer."""
        for category, items in failed_buffer.items():
            if category not in cls._buffer:
                cls._buffer[category] = {}
            
            for identifier, count in items.items():
                count = cls._normalize_count(count)
                cls._buffer[category][identifier] = cls._buffer[category].get(identifier, 0) + count
        
        cls._dirty = True
    
    @classmethod
    def save_to_disk(cls) -> Optional[float]:
        """
        Periodic task to merge buffer into JSON files.
        
        This is registered as a Blender persistent timer. Returning a float
        causes Blender to automatically re-schedule the timer for that many seconds.
        Returning None stops the timer.
        
        Returns:
            Interval in seconds until next save, or None to stop timer.
        """
        # Check if timer should stop (set by preference change callback)
        # This prevents duplicate timer registration during interval changes
        if cls.timer_should_stop:
            cls.timer_should_stop = False
            return None  # Stop this timer instance, new one will be registered
        
        # Get configured interval
        prefs = cls._get_preferences()
        interval = cls.DEFAULT_INTERVAL
        
        if prefs:
            interval = float(getattr(prefs, 'stats_auto_export_interval', cls.DEFAULT_INTERVAL))
            if interval <= 0:
                return cls.DISABLED_CHECK_INTERVAL
        
        # Skip if no new data
        if not cls._dirty:
            return interval
        
        # Get internal file path
        internal_path = cls.get_internal_file_path()
        if not internal_path:
            return interval
        
        # Atomically swap buffer
        current_buffer = cls._buffer
        cls._buffer = {"operators": {}, "chords": {}}
        cls._dirty = False
        
        # Load and merge data
        data = cls._load_data_from_file(internal_path)
        cls._merge_buffer_into_data(data, current_buffer)
        
        # Save to internal file
        internal_success = cls._write_json_file(internal_path, data)
        
        # Save to export path if configured
        export_success = False
        export_path = cls._get_export_path()
        if export_path:
            export_success = cls._write_json_file(export_path, data, sort_keys=True)
        
        # Handle failures
        if not internal_success and not export_success:
            cls._restore_buffer(current_buffer)
        
        return interval
    
    @classmethod
    def clear_all(cls) -> None:
        """Reset all statistics (buffer and internal file)."""
        cls._buffer = {"operators": {}, "chords": {}}
        cls._dirty = False
        
        path = cls.get_internal_file_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
    
    @classmethod
    def get_stats(cls, category: str) -> Dict[str, int]:
        """
        Get all statistics for a given category.
        
        Args:
            category: Category to retrieve ('operators', 'chords')
            
        Returns:
            Dictionary mapping identifier to count.
        """
        result = {}
        
        # Load from internal file
        path = cls.get_internal_file_path()
        if path:
            data = cls._load_data_from_file(path)
            if category in data:
                for identifier, value in data[category].items():
                    result[identifier] = cls._normalize_count(value)
        
        # Merge with buffer
        if category in cls._buffer:
            for identifier, value in cls._buffer[category].items():
                count = cls._normalize_count(value)
                result[identifier] = result.get(identifier, 0) + count
        
        return result
