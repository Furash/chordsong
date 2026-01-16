"""Operators for manually reordering chord mappings."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy  # type: ignore

from ..common import prefs


def _update_order_indices(mappings):
    """Update order_index for all mappings to match their current array position."""
    for idx, m in enumerate(mappings):
        m.order_index = idx


class CHORDSONG_OT_Mapping_Move_Up(bpy.types.Operator):
    """Move this chord mapping up in the list."""

    bl_idname = "chordsong.mapping_move_up"
    bl_label = "Move Up"
    bl_description = "Move this chord up in the list"
    bl_options = {"INTERNAL"}

    # Store the actual chord string to find the real index
    chord: bpy.props.StringProperty()

    def execute(self, context: bpy.types.Context):
        """Move mapping up within its group."""
        p = prefs(context)
        
        # Find the chord and its group
        actual_idx = None
        current_group = None
        for idx, m in enumerate(p.mappings):
            if getattr(m, "chord", "") == self.chord:
                actual_idx = idx
                current_group = getattr(m, "group", "")
                break
        
        if actual_idx is None or actual_idx <= 0:
            return {"CANCELLED"}
        
        # Find the previous chord in the SAME group
        target_idx = None
        for idx in range(actual_idx - 1, -1, -1):
            if getattr(p.mappings[idx], "group", "") == current_group:
                target_idx = idx
                break
        
        if target_idx is None:
            # Already at top of group
            return {"CANCELLED"}
        
        # Move to just before the target (swap positions)
        p.mappings.move(actual_idx, target_idx)
        
        # Update order indices to match new positions
        _update_order_indices(p.mappings)
        
        # Force UI redraw to show new indices
        for area in context.screen.areas:
            area.tag_redraw()
        
        return {"FINISHED"}


class CHORDSONG_OT_Mapping_Move_Down(bpy.types.Operator):
    """Move this chord mapping down in the list."""

    bl_idname = "chordsong.mapping_move_down"
    bl_label = "Move Down"
    bl_description = "Move this chord down in the list"
    bl_options = {"INTERNAL"}

    # Store the actual chord string to find the real index
    chord: bpy.props.StringProperty()

    def execute(self, context: bpy.types.Context):
        """Move mapping down within its group."""
        p = prefs(context)
        
        # Find the chord and its group
        actual_idx = None
        current_group = None
        for idx, m in enumerate(p.mappings):
            if getattr(m, "chord", "") == self.chord:
                actual_idx = idx
                current_group = getattr(m, "group", "")
                break
        
        if actual_idx is None or actual_idx >= len(p.mappings) - 1:
            return {"CANCELLED"}
        
        # Find the next chord in the SAME group
        target_idx = None
        for idx in range(actual_idx + 1, len(p.mappings)):
            if getattr(p.mappings[idx], "group", "") == current_group:
                target_idx = idx
                break
        
        if target_idx is None:
            # Already at bottom of group
            return {"CANCELLED"}
        
        # Move to just after the target (swap positions)
        p.mappings.move(actual_idx, target_idx)
        
        # Update order indices to match new positions
        _update_order_indices(p.mappings)
        
        # Force UI redraw to show new indices
        for area in context.screen.areas:
            area.tag_redraw()
        
        return {"FINISHED"}


class CHORDSONG_OT_Mapping_Sort_Group(bpy.types.Operator):
    """Sort chord mappings within a group alphabetically by chord."""

    bl_idname = "chordsong.mapping_sort_group"
    bl_label = "Sort Group"
    bl_description = "Sort chord mappings within this group alphabetically"
    bl_options = {"INTERNAL"}

    group_name: bpy.props.StringProperty()

    def execute(self, context: bpy.types.Context):
        """Sort mappings within the specified group."""
        p = prefs(context)
        
        # Find all mappings in this group
        group_mappings = []
        for idx, m in enumerate(p.mappings):
            if getattr(m, "group", "") == self.group_name:
                chord_str = getattr(m, "chord", "").lower()
                # Store chord string for identification
                group_mappings.append((chord_str, getattr(m, "chord", "")))
        
        if len(group_mappings) <= 1:
            self.report({"INFO"}, "Group has 0 or 1 chord, nothing to sort")
            return {"CANCELLED"}
        
        # Sort by chord string (lowercase for sorting)
        group_mappings.sort(key=lambda x: x[0])
        
        # Get just the chord strings in sorted order
        sorted_chords = [chord for _, chord in group_mappings]
        
        # Find where the first chord of this group is
        first_position = None
        for idx, m in enumerate(p.mappings):
            if getattr(m, "group", "") == self.group_name:
                first_position = idx
                break
        
        if first_position is None:
            return {"CANCELLED"}
        
        # Move each chord to its sorted position
        for target_offset, target_chord in enumerate(sorted_chords):
            # Find current position of this chord
            current_idx = None
            for idx, m in enumerate(p.mappings):
                if getattr(m, "chord", "") == target_chord and getattr(m, "group", "") == self.group_name:
                    current_idx = idx
                    break
            
            if current_idx is not None:
                target_idx = first_position + target_offset
                if current_idx != target_idx:
                    p.mappings.move(current_idx, target_idx)
        
        # Update order indices to match new positions
        _update_order_indices(p.mappings)
        
        # Force UI redraw to show new indices
        for area in context.screen.areas:
            area.tag_redraw()
        
        count = len(sorted_chords)
        self.report({"INFO"}, f"Sorted {count} chords in group '{self.group_name}'")
        return {"FINISHED"}
