"""Normalize order indices operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name

import bpy  # type: ignore

from ..common import prefs, schedule_autosave_safe
from ...core.config_io import _normalize_order_indices


class CHORDSONG_OT_Mapping_Normalize_Indices(bpy.types.Operator):
    """Normalize order indices to sequential values (0, 1, 2...)"""

    bl_idname = "chordsong.mapping_normalize_indices"
    bl_label = "Normalize Order Indices"
    bl_description = "Fix order indices to be sequential with no gaps"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        """Normalize all order indices."""
        p = prefs(context)

        if not p.mappings:
            self.report({"INFO"}, "No mappings to normalize")
            return {"CANCELLED"}

        # Normalize indices
        _normalize_order_indices(p.mappings)

        count = len(p.mappings)
        self.report({"INFO"}, f"Normalized {count} chord indices")

        # Trigger autosave
        schedule_autosave_safe(p, delay_s=1.0)

        return {"FINISHED"}
