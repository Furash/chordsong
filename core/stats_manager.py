"""Statistics manager for tracking operator, chord, and property usage."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json
import os
import bpy

class CS_StatsManager:
    """
    Singleton-style statistics manager that tracks operator, chord, and property usage.
    Uses an in-memory buffer and periodic writes to disk to ensure zero performance impact.
    """
    
    _buffer = {"operators": {}, "chords": {}, "properties": {}}
    _dirty = False
    _cached_path = None
    _refresh_timer_registered = False
    
    # INFO panel property tracking
    _info_panel_handler_registered = False
    _last_info_panel_content = ""  # Track last seen content to detect new entries
    _temp_clipboard_buffer = ""  # Temporary buffer to avoid touching user's clipboard
    
    @classmethod
    def _get_addon_package(cls):
        """Get the root addon package name."""
        from ..utils.addon_package import addon_root_package
        return addon_root_package(__package__)
    
    @classmethod
    def get_file_path(cls):
        """
        Get the path to the statistics JSON file in the user's writable directory.
        
        Uses extension_path_user for Blender 4.2+ extensions (recommended),
        with fallback to user_resource for backward compatibility.
        """
        # Return cached path if available
        if cls._cached_path and os.path.exists(os.path.dirname(cls._cached_path)):
            return cls._cached_path
        
        # Try extension_path_user first (Blender 4.2+, recommended for extensions)
        if hasattr(bpy.utils, 'extension_path_user'):
            try:
                pkg = cls._get_addon_package()
                extension_dir = bpy.utils.extension_path_user(pkg, path="", create=True)
                if extension_dir:
                    cls._cached_path = os.path.join(extension_dir, "chordsong_stats.json")
                    return cls._cached_path
            except Exception:
                pass

        # Last resort fallback (should never happen)
        return ""

    @classmethod
    def record(cls, category, identifier):
        """
        Record a statistics event to the internal buffer.
        
        Args:
            category: Category of the event ('operators', 'chords', 'properties')
            identifier: String identifier for the event (e.g., 'mesh.select_all', 'G X')
        """
        cat = cls._buffer.get(category)
        if cat is not None:
            cat[identifier] = cat.get(identifier, 0) + 1
            cls._dirty = True
            # Schedule UI refresh if stats tab is visible
            cls._schedule_ui_refresh()
    
    @classmethod
    def _schedule_ui_refresh(cls):
        """Schedule a debounced UI refresh if the stats tab is visible and realtime refresh is enabled."""
        try:
            # Check if stats tab is visible and realtime refresh is enabled
            from ..utils.addon_package import addon_root_package
            pkg = addon_root_package(__package__)
            if pkg and pkg in bpy.context.preferences.addons:
                prefs = bpy.context.preferences.addons[pkg].preferences
                if (hasattr(prefs, 'prefs_tab') and prefs.prefs_tab == "STATS" and
                    hasattr(prefs, 'stats_realtime_refresh') and prefs.stats_realtime_refresh):
                    # Register a one-time timer for debounced refresh
                    # If timer already registered, it will be reset by the new registration
                    cls._refresh_timer_registered = True
                    # Unregister existing timer if any, then register new one
                    try:
                        bpy.app.timers.unregister(cls._debounced_refresh)
                    except ValueError:
                        pass  # Timer not registered, that's fine
                    bpy.app.timers.register(cls._debounced_refresh, first_interval=0.5)
        except Exception:
            pass  # Silently fail if context is invalid
    
    @classmethod
    def _debounced_refresh(cls):
        """Debounced refresh function called by timer."""
        cls._refresh_timer_registered = False
        try:
            from ..utils.addon_package import addon_root_package
            
            pkg = addon_root_package(__package__)
            if pkg and pkg in bpy.context.preferences.addons:
                prefs = bpy.context.preferences.addons[pkg].preferences
                # Only refresh if stats tab is still visible
                if hasattr(prefs, 'prefs_tab') and prefs.prefs_tab == "STATS":
                    # Import here to avoid circular dependency
                    from ..operators.stats_operators import _refresh_stats_ui
                    _refresh_stats_ui(prefs, export_to_file=False)
        except Exception:
            pass  # Silently fail if context is invalid
        
        return None  # One-time timer

    @classmethod
    def save_to_disk(cls):
        """
        Periodic task to merge buffer into the physical JSON file.
        Returns interval in seconds to re-run based on user preference.
        """
        # Get auto-export interval from preferences
        interval = 180.0  # Default fallback
        try:
            from ..utils.addon_package import addon_root_package
            pkg = addon_root_package(__package__)
            if pkg and pkg in bpy.context.preferences.addons:
                prefs = bpy.context.preferences.addons[pkg].preferences
                interval = float(getattr(prefs, 'stats_auto_export_interval', 180))
                if interval <= 0:
                    # Auto-export disabled, check again in 60 seconds
                    return 60.0
        except Exception:
            interval = 180.0  # Fallback to default on error
        
        # Only save if there's dirty data to write
        if not cls._dirty:
            return interval  # Re-run at configured interval

        path = cls.get_file_path()
        if not path:
            # Unable to determine valid path, skip save but keep buffer
            return interval
        
        data = {}

        # Load existing data if file exists
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # Merge buffer into file data
        for cat, items in cls._buffer.items():
            if cat not in data:
                data[cat] = {}
            for k, v in items.items():
                # Handle both formats: convert dicts to counts
                # Buffer value (should be int, but handle dict just in case)
                buffer_count = v.get("count", v) if isinstance(v, dict) else v
                
                # File value (might be dict from old format)
                existing_value = data[cat].get(k, 0)
                file_count = existing_value.get("count", existing_value) if isinstance(existing_value, dict) else existing_value
                
                # Merge as simple count
                data[cat][k] = file_count + buffer_count

        # Write updated data back to disk
        # Ensure parent directory exists
        try:
            parent_dir = os.path.dirname(path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception:
            # If save fails, keep buffer for next attempt
            return interval

        # Clear buffer and reset dirty flag only after successful save
        cls._buffer = {"operators": {}, "chords": {}, "properties": {}}
        cls._dirty = False
        return interval

    @classmethod
    def clear_all(cls):
        """Reset all statistics (both buffer and file)."""
        cls._buffer = {"operators": {}, "chords": {}, "properties": {}}
        cls._dirty = False
        path = cls.get_file_path()
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    @classmethod
    def get_stats(cls, category):
        """
        Get all statistics for a given category, including both buffer and saved data.
        
        Args:
            category: Category to retrieve ('operators', 'chords', 'properties')
            
        Returns:
            Dictionary of {identifier: count}
        """
        result = {}
        
        # Load from file
        path = cls.get_file_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if category in data:
                        # Handle both legacy format (just numbers) and metadata format (dicts)
                        for identifier, value in data[category].items():
                            if isinstance(value, dict):
                                # Convert metadata format to simple count
                                result[identifier] = value.get("count", 0)
                            else:
                                # Legacy format (just a number)
                                result[identifier] = value
            except Exception:
                pass
        
        # Merge with buffer
        if category in cls._buffer:
            for k, v in cls._buffer[category].items():
                # Handle both formats in buffer too
                if isinstance(v, dict):
                    count = v.get("count", 0)
                else:
                    count = v
                result[k] = result.get(k, 0) + count
        
        return result
    
    @classmethod
    def _parse_bpy_context_from_info_panel(cls, text):
        """
        Parse bpy.context entries from INFO panel text.
        Extracts property paths like bpy.context.tool_settings.use_snap
        
        Args:
            text: INFO panel text content
            
        Returns:
            Set of property paths found
        """
        import re
        property_paths = set()
        
        if not text:
            return property_paths
        
        # Pattern to match bpy.context.property.path patterns
        # Matches: bpy.context.tool_settings.use_snap
        # Matches: bpy.context.scene.frame_current
        # Matches: bpy.context.object.location
        # Also matches with assignments: bpy.context.object.location = (1, 2, 3)
        pattern = r'bpy\.context\.([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)'
        
        for match in re.finditer(pattern, text):
            path = match.group(1)  # Get the path after bpy.context.
            if path:
                property_paths.add(path)
        
        return property_paths
    
    @classmethod
    def _info_panel_timer(cls):
        """Timer-based handler to track property usage from INFO panel."""
        try:
            # Check if statistics and property tracking are enabled
            from ..utils.addon_package import addon_root_package
            pkg = addon_root_package(__package__)
            if pkg and pkg in bpy.context.preferences.addons:
                prefs = bpy.context.preferences.addons[pkg].preferences
                if not getattr(prefs, 'enable_stats', False):
                    # Unregister timer if stats are disabled
                    cls.unregister_info_panel_tracking()
                    return None  # Stop timer
                if not getattr(prefs, 'stats_track_properties', False):
                    # Unregister timer if property tracking is disabled
                    cls.unregister_info_panel_tracking()
                    return None  # Stop timer
            else:
                # Can't access preferences, stop timer
                cls.unregister_info_panel_tracking()
                return None  # Stop timer
            
            # Check if Blender window is valid before proceeding
            # Skip clipboard operations if window context is invalid
            try:
                if not bpy.context.window or not bpy.context.window.screen:
                    return 2.0  # No active window, skip this cycle
            except (AttributeError, RuntimeError, ReferenceError):
                # Window context is invalid (Blender might be out of focus or closing)
                # Return None to stop timer and prevent crashes
                return None
            except Exception:
                # Any other exception - stop timer to prevent crashes
                return None
            
            # Try to get INFO panel content - only if INFO panel is actually open
            # Use a temporary buffer instead of touching user's clipboard
            try:
                # Safely check if screen and areas are accessible
                try:
                    screen = bpy.context.screen
                    if not screen:
                        return 2.0  # No screen, skip this cycle
                except (AttributeError, RuntimeError, ReferenceError):
                    # Screen context is invalid (Blender might be out of focus or closing)
                    return None  # Stop timer to prevent crashes
                
                # Find existing INFO area (don't create or switch areas)
                info_area = None
                try:
                    for area in screen.areas:
                        try:
                            if area.type == 'INFO':
                                info_area = area
                                break
                        except (AttributeError, RuntimeError, ReferenceError):
                            # Area is invalid, skip it
                            continue
                except (AttributeError, RuntimeError, ReferenceError):
                    # Areas list is invalid
                    return None  # Stop timer to prevent crashes
                
                # Only proceed if INFO panel is actually open
                if info_area:
                    # Use temp_override to work with INFO area
                    try:
                        with bpy.context.temp_override(area=info_area):
                            try:
                                wm = bpy.context.window_manager
                                if not wm:
                                    return 2.0  # No window manager, skip
                                
                                # Store current clipboard in our buffer to restore later
                                try:
                                    cls._temp_clipboard_buffer = wm.clipboard
                                except (AttributeError, RuntimeError, ReferenceError):
                                    # Clipboard access failed, likely Blender is out of focus
                                    return None  # Stop timer to prevent crashes
                                
                                # Try to copy all reports without select_all (less disruptive)
                                # First try with select_all, but if it fails, try without
                                try:
                                    bpy.ops.info.select_all()
                                    bpy.ops.info.report_copy()
                                except (AttributeError, RuntimeError, ReferenceError):
                                    # Operations failed, likely Blender is out of focus
                                    # Try to restore clipboard and stop timer
                                    try:
                                        wm.clipboard = cls._temp_clipboard_buffer
                                    except Exception:
                                        pass
                                    return None  # Stop timer to prevent crashes
                                except Exception:
                                    # If select_all fails (maybe UI is busy), 
                                    # try just report_copy
                                    # This will only copy selected text, but it's less disruptive
                                    try:
                                        bpy.ops.info.report_copy()
                                    except (AttributeError, RuntimeError, ReferenceError):
                                        # Operations failed, likely Blender is out of focus
                                        # Try to restore clipboard and stop timer
                                        try:
                                            wm.clipboard = cls._temp_clipboard_buffer
                                        except Exception:
                                            pass
                                        return None  # Stop timer to prevent crashes
                                    except Exception:
                                        # If both fail, skip this cycle (likely Blender is out of focus or UI is busy)
                                        # Restore clipboard and return early to avoid unnecessary operations
                                        try:
                                            wm.clipboard = cls._temp_clipboard_buffer
                                        except Exception:
                                            pass
                                        return 2.0
                                
                                # Get the copied content immediately
                                try:
                                    new_clipboard = wm.clipboard
                                except (AttributeError, RuntimeError, ReferenceError):
                                    # Clipboard access failed, restore and stop
                                    try:
                                        wm.clipboard = cls._temp_clipboard_buffer
                                    except Exception:
                                        pass
                                    return None  # Stop timer to prevent crashes
                                
                                # Restore clipboard immediately from our buffer
                                try:
                                    wm.clipboard = cls._temp_clipboard_buffer
                                except (AttributeError, RuntimeError, ReferenceError):
                                    # Can't restore, but continue processing
                                    pass
                                
                                # Only process if content changed and we got new content
                                # If content hasn't changed, skip processing to avoid unnecessary work
                                if new_clipboard and new_clipboard != cls._last_info_panel_content:
                                    # Get only the new lines
                                    old_lines = set(cls._last_info_panel_content.splitlines())
                                    new_lines = new_clipboard.splitlines()
                                    
                                    # Find new lines
                                    new_content_lines = []
                                    for line in new_lines:
                                        if line not in old_lines:
                                            new_content_lines.append(line)
                                    
                                    # Only process if we actually have new content
                                    if new_content_lines:
                                        new_content = '\n'.join(new_content_lines)
                                        # Parse bpy.context entries from new content
                                        property_paths = cls._parse_bpy_context_from_info_panel(new_content)
                                        
                                        # Record each property path found
                                        for path in property_paths:
                                            cls.record("properties", path)
                                    
                                    # Update last seen content only if we got new content
                                    cls._last_info_panel_content = new_clipboard
                                # If no new content, we've already restored clipboard, so just return
                                # This avoids unnecessary processing when nothing changes
                            except (AttributeError, RuntimeError, ReferenceError):
                                # Context is invalid, stop timer to prevent crashes
                                return None
                            except Exception:
                                # Try to restore clipboard if something went wrong
                                try:
                                    wm = bpy.context.window_manager
                                    if wm:
                                        wm.clipboard = cls._temp_clipboard_buffer
                                except Exception:
                                    pass
                                return 2.0  # Continue but skip this cycle
                    except (AttributeError, RuntimeError, ReferenceError):
                        # Context override failed, likely Blender is out of focus
                        return None  # Stop timer to prevent crashes
                else:
                    # INFO panel not open - don't track, but keep last content for when it opens again
                    pass
            except (AttributeError, RuntimeError, ReferenceError):
                # Context is invalid, stop timer to prevent crashes
                return None
            except Exception:
                # Other exceptions - continue but skip this cycle
                return 2.0
            
        except (AttributeError, RuntimeError, ReferenceError):
            # Context is invalid, stop timer to prevent crashes
            return None
        except Exception:
            # Other exceptions - continue but skip this cycle
            return 2.0
        
        return 2.0  # Check every 2 seconds
    
    @classmethod
    def _update_property_tracking(cls, prefs):
        """Update property tracking registration based on toggle state."""
        if getattr(prefs, 'stats_track_properties', False) and getattr(prefs, 'enable_stats', False):
            cls.register_info_panel_tracking()
        else:
            cls.unregister_info_panel_tracking()
    
    @classmethod
    def register_info_panel_tracking(cls):
        """Register the INFO panel property tracking timer."""
        if not cls._info_panel_handler_registered:
            if not bpy.app.timers.is_registered(cls._info_panel_timer):
                bpy.app.timers.register(cls._info_panel_timer, first_interval=2.0)
                cls._info_panel_handler_registered = True
                cls._last_info_panel_content = ""
                cls._temp_clipboard_buffer = ""
    
    @classmethod
    def unregister_info_panel_tracking(cls):
        """Unregister the INFO panel property tracking timer."""
        if cls._info_panel_handler_registered:
            if bpy.app.timers.is_registered(cls._info_panel_timer):
                bpy.app.timers.unregister(cls._info_panel_timer)
                cls._info_panel_handler_registered = False
                cls._last_info_panel_content = ""
                cls._temp_clipboard_buffer = ""
