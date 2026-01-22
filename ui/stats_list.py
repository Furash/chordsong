"""UI List for displaying statistics."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json
from typing import Set
from bpy.types import UIList

from ..utils.addon_package import addon_root_package


# Column width constants
COL_ICON_WIDTH = 2.0
COL_INFO_WIDTH = 18.0
COL_HOTKEY_WIDTH = 4.0
COL_COUNT_WIDTH = 3.0
COL_BLACKLIST_WIDTH = 2.0


class CHORDSONG_UL_Stats(UIList):
    """UIList for displaying statistics in a sortable table."""
    
    # Cache blacklist per draw cycle to avoid repeated parsing
    _cached_blacklist: Set[str] = set()
    _cache_valid = False
    
    # Cache hotkeys per draw cycle for performance
    _cached_hotkeys: dict = {}
    _hotkey_cache_valid = False
    
    @classmethod
    def _get_blacklist(cls, prefs) -> Set[str]:
        """Get blacklist set (cached within draw cycle)."""
        if not cls._cache_valid:
            try:
                blacklist_json = getattr(prefs, 'stats_blacklist', '[]')
                cls._cached_blacklist = set(json.loads(blacklist_json))
            except (json.JSONDecodeError, TypeError):
                cls._cached_blacklist = set()
            cls._cache_valid = True
        
        return cls._cached_blacklist
    
    @classmethod
    def _normalize_operator_name(cls, operator_name: str) -> str:
        """
        Normalize operator name to idname format.
        
        Stats might store as 'mesh.select_all' or 'MESH_OT_select_all',
        but keymaps use 'mesh.select_all'.
        
        Args:
            operator_name: Name from stats (various formats)
            
        Returns:
            Normalized idname (e.g., 'mesh.select_all')
        """
        # Already in correct format
        if '.' in operator_name and '_OT_' not in operator_name:
            return operator_name
        
        # Convert CLASS_OT_name to class.name format
        if '_OT_' in operator_name:
            parts = operator_name.split('_OT_', 1)
            if len(parts) == 2:
                return f"{parts[0].lower()}.{parts[1].lower()}"
        
        # Fallback: return as-is
        return operator_name
    
    @classmethod
    def _get_operator_hotkey(cls, operator_name: str) -> str:
        """
        Get the first hotkey assigned to an operator (cached per draw cycle).
        
        Args:
            operator_name: Operator name (various formats)
            
        Returns:
            Hotkey string (e.g., 'Ctrl+A') or empty string if no hotkey found.
        """
        # Normalize operator name first
        normalized_name = cls._normalize_operator_name(operator_name)
        
        # Check cache first
        if cls._hotkey_cache_valid and normalized_name in cls._cached_hotkeys:
            return cls._cached_hotkeys[normalized_name]
        
        import bpy
        
        hotkey = ""
        
        try:
            # Get the window manager's key configs
            wm = bpy.context.window_manager
            if not wm or not hasattr(wm, 'keyconfigs'):
                return ""
            
            # Check all keyconfigs (including addon keymaps)
            for kc_name in wm.keyconfigs.keys():
                kc = wm.keyconfigs.get(kc_name)
                if not kc:
                    continue
                
                # Search through all keymaps
                for km in kc.keymaps:
                    if not hasattr(km, 'keymap_items'):
                        continue
                    
                    for kmi in km.keymap_items:
                        try:
                            if kmi.idname == normalized_name and kmi.active:
                                # Build hotkey string
                                parts = []
                                
                                # Add modifiers in standard order
                                if kmi.ctrl:
                                    parts.append('Ctrl')
                                if kmi.alt:
                                    parts.append('Alt')
                                if kmi.shift:
                                    parts.append('Shift')
                                if kmi.oskey:
                                    parts.append('Cmd' if bpy.app.platform == 'DARWIN' else 'Win')
                                
                                # Add the key itself
                                key_name = kmi.type
                                if key_name and key_name not in ('NONE', ''):
                                    # Clean up key name for display
                                    display_key = key_name.replace('_', ' ')
                                    # Keep single letters as-is, title case others
                                    if len(display_key) == 1:
                                        parts.append(display_key)
                                    else:
                                        parts.append(display_key.title())
                                
                                if parts:
                                    hotkey = '+'.join(parts)
                                    break
                        except (AttributeError, RuntimeError, TypeError):
                            continue
                    
                    if hotkey:
                        break
                
                if hotkey:
                    break
        except Exception:
            # Fail gracefully
            pass
        
        # Cache the result (even if empty)
        cls._cached_hotkeys[normalized_name] = hotkey
        cls._hotkey_cache_valid = True
        
        return hotkey
    
    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname):
        """Draw a single statistics item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            self._draw_default_layout(context, layout, item)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=str(item.count))
    
    def _draw_default_layout(self, context, layout, item):
        """Draw default row layout."""
        row = layout.row(align=True)
        
        # Column 1: Type indicator or convert button
        self._draw_type_column(row, item)
        
        # Column 2: Item info
        self._draw_info_column(row, item)
        
        # Column 3: Hotkey (operators only)
        self._draw_hotkey_column(row, item)
        
        # Column 4: Usage count
        self._draw_count_column(row, item)
        
        # Column 5: Blacklist toggle
        self._draw_blacklist_column(context, row, item)
    
    def _draw_type_column(self, row, item):
        """Draw type indicator column."""
        col = row.row(align=True)
        col.ui_units_x = COL_ICON_WIDTH
        
        if item.category == 'chords':
            col.label(text="", icon='NODE_SOCKET_GEOMETRY')
        else:
            op = col.operator(
                "chordsong.stats_convert_to_chord",
                text="",
                icon='EVENT_C',
                emboss=True
            )
            op.category = item.category
            op.stats_name = item.name
    
    def _draw_info_column(self, row, item):
        """Draw item information column."""
        col = row.row(align=True)
        col.ui_units_x = COL_INFO_WIDTH
        
        if item.category == 'chords':
            group = item.group or "(Ungrouped)"
            label = item.label or "(No label)"
            text = f"{item.name}     {group} : {label}"
        else:
            text = f"{item.category.capitalize()}: {item.name}"
        
        col.label(text=text)
    
    def _draw_hotkey_column(self, row, item):
        """Draw hotkey column (operators only)."""
        col = row.row(align=True)
        col.ui_units_x = COL_HOTKEY_WIDTH
        
        if item.category == 'operators':
            hotkey = self._get_operator_hotkey(item.name)
            if hotkey:
                # Use lighter gray text color for hotkeys
                col.label(text=hotkey)
            else:
                col.label(text="")
        else:
            # Chords don't have hotkeys, show empty
            col.label(text="")
    
    def _draw_count_column(self, row, item):
        """Draw usage count column."""
        col = row.row(align=True)
        col.ui_units_x = COL_COUNT_WIDTH
        col.label(text=str(item.count))
    
    def _draw_blacklist_column(self, context, row, item):
        """Draw blacklist toggle column."""
        col = row.row(align=True)
        col.ui_units_x = COL_BLACKLIST_WIDTH
        
        try:
            pkg = addon_root_package(__package__)
            prefs = context.preferences.addons[pkg].preferences
            
            blacklist_key = f"{item.category}:{item.name}"
            blacklist = self._get_blacklist(prefs)
            is_blacklisted = blacklist_key in blacklist
            
            op = col.operator(
                "chordsong.stats_blacklist",
                text="",
                icon='CHECKBOX_HLT' if is_blacklisted else 'TRASH',
                emboss=False
            )
            op.action = 'TOGGLE'
            op.category = item.category
            op.name = item.name
        except (AttributeError, KeyError):
            col.label(text="")
    
    def filter_items(self, _context, _data, _propname):
        """Filter items - not used but required by UIList."""
        # Invalidate caches on filter call (signals new draw cycle)
        cls = type(self)
        cls._cache_valid = False  # pylint: disable=protected-access
        cls._hotkey_cache_valid = False  # pylint: disable=protected-access
        cls._cached_hotkeys = {}  # pylint: disable=protected-access
        return [], []
