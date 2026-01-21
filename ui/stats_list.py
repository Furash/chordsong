"""UI List for displaying statistics."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json
from bpy.types import UIList

from ..utils.addon_package import addon_root_package


class CHORDSONG_UL_Stats(UIList):
    """UIList for displaying statistics in a sortable table."""
    
    def draw_item(self, context, layout, _data, item, _icon, _active_data, _active_propname):
        """Draw a single statistics item."""
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            # Grid layout with fixed column widths (adjust these factors as needed)
            row = layout.row(align=True)
            
            # Column 1: Icon (for chords) OR Convert button (for operators)
            col1 = row.row(align=True)
            col1.ui_units_x = 2.0  # Icon/button width
            if item.category == 'chords':
                type_icon = 'NODE_SOCKET_GEOMETRY'
                col1.label(text="", icon=type_icon)
            else:
                op = col1.operator(
                    "chordsong.stats_convert_to_chord",
                    text="",
                    icon='EVENT_C',
                    emboss=True
                )
                op.category = item.category
                op.stats_name = item.name
            
            # Column 2: Chord + Group : Label (for chords) OR Category: Name (for operators)
            col2 = row.row(align=True)
            col2.ui_units_x = 18.0  # Combined chord info or operator info
            if item.category == 'chords':
                group_text = item.group or "(Ungrouped)"
                label_text = item.label or "(No label)"
                combined_text = f"{item.name}     {group_text} : {label_text}"
                col2.label(text=combined_text)
            else:
                col2.label(text=f"{item.category.capitalize()}: {item.name}")
            
            # Column 3: Count
            col3 = row.row(align=True)
            col3.ui_units_x = 3.0  # Usage count
            col3.label(text=str(item.count))
            
            # Column 4: Blacklist button
            col4 = row.row(align=True)
            col4.ui_units_x = 2.0  # Trash/blacklist button
            try:
                package_name = addon_root_package(__package__)
                prefs = context.preferences.addons[package_name].preferences
                
                blacklist_key = f"{item.category}:{item.name}"
                blacklist_json = prefs.stats_blacklist or "[]"
                blacklist = set(json.loads(blacklist_json))
                is_blacklisted = blacklist_key in blacklist

                op = col4.operator(
                    "chordsong.stats_blacklist",
                    text="",
                    icon='CHECKBOX_HLT' if is_blacklisted else 'TRASH',
                    emboss=False
                )
                op.action = 'TOGGLE'
                op.category = item.category
                op.name = item.name
                
            except Exception:
                col4.label(text="")  # Empty cell if error
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text=str(item.count))
    
    def filter_items(self, _context, _data, _propname):
        """Filter items - not used but required by UIList."""
        # We handle filtering in the refresh operator instead
        return [], []
