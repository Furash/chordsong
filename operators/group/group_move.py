"""Group move operators for reordering groups."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,relative-beyond-top-level

import bpy
from bpy.props import IntProperty

from ..common import prefs


class CHORDSONG_OT_Group_Move_Up(bpy.types.Operator):
    """Move group up in the list."""

    bl_idname = "chordsong.group_move_up"
    bl_label = "Move Group Up"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    index: IntProperty(
        name="Index",
        description="Index of the group to move",
        default=-1,
    )

    def execute(self, context):
        """Move the group up."""
        p = prefs(context)

        idx = int(self.index)
        if idx < 0 or idx >= len(p.groups):
            self.report({"WARNING"}, "Invalid group index")
            return {"CANCELLED"}

        # Normalize stored indices to avoid "gaps" accumulating
        from ...core.config_io import _normalize_group_indices
        _normalize_group_indices(p.groups)

        if idx == 0:
            # Already at the top
            return {"CANCELLED"}

        # Move relative to the currently visible groups in this context tab.
        # This avoids needing multiple clicks to move past "hidden" groups.
        current_ctx = getattr(p, "mapping_context_tab", "VIEW_3D")
        visible_names = set()
        for m in getattr(p, "mappings", []):
            m_ctx = getattr(m, "context", "VIEW_3D")
            if m_ctx != current_ctx and m_ctx != "ALL":
                continue
            g = (getattr(m, "group", "") or "").strip()
            if g:
                visible_names.add(g)

        visible_indices = [
            i for i, grp in enumerate(p.groups)
            if (getattr(grp, "name", "") or "").strip() and (getattr(grp, "name", "") or "").strip() in visible_names
        ]

        if idx in visible_indices:
            pos = visible_indices.index(idx)
            if pos == 0:
                return {"CANCELLED"}
            target_idx = visible_indices[pos - 1]
        else:
            # Fallback: behave like a normal list move
            target_idx = idx - 1

        p.groups.move(idx, target_idx)
        _normalize_group_indices(p.groups)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=3.0)

        # Ensure overlay reflects new group order immediately
        try:
            from ...ui.overlay import clear_overlay_cache
            clear_overlay_cache()
        except Exception:
            pass

        return {"FINISHED"}


class CHORDSONG_OT_Group_Move_Down(bpy.types.Operator):
    """Move group down in the list."""

    bl_idname = "chordsong.group_move_down"
    bl_label = "Move Group Down"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    index: IntProperty(
        name="Index",
        description="Index of the group to move",
        default=-1,
    )

    def execute(self, context):
        """Move the group down."""
        p = prefs(context)

        idx = int(self.index)
        if idx < 0 or idx >= len(p.groups):
            self.report({"WARNING"}, "Invalid group index")
            return {"CANCELLED"}

        # Normalize stored indices to avoid "gaps" accumulating
        from ...core.config_io import _normalize_group_indices
        _normalize_group_indices(p.groups)

        if idx >= len(p.groups) - 1:
            # Already at the bottom
            return {"CANCELLED"}

        # Move relative to the currently visible groups in this context tab.
        # This avoids needing multiple clicks to move past "hidden" groups.
        current_ctx = getattr(p, "mapping_context_tab", "VIEW_3D")
        visible_names = set()
        for m in getattr(p, "mappings", []):
            m_ctx = getattr(m, "context", "VIEW_3D")
            if m_ctx != current_ctx and m_ctx != "ALL":
                continue
            g = (getattr(m, "group", "") or "").strip()
            if g:
                visible_names.add(g)

        visible_indices = [
            i for i, grp in enumerate(p.groups)
            if (getattr(grp, "name", "") or "").strip() and (getattr(grp, "name", "") or "").strip() in visible_names
        ]

        if idx in visible_indices:
            pos = visible_indices.index(idx)
            if pos >= len(visible_indices) - 1:
                return {"CANCELLED"}
            target_idx = visible_indices[pos + 1]
        else:
            # Fallback: behave like a normal list move
            target_idx = idx + 1

        p.groups.move(idx, target_idx)
        _normalize_group_indices(p.groups)

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=3.0)

        # Ensure overlay reflects new group order immediately
        try:
            from ...ui.overlay import clear_overlay_cache
            clear_overlay_cache()
        except Exception:
            pass

        return {"FINISHED"}
