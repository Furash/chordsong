"""Group cleanup operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy

from .common import prefs


class CHORDSONG_OT_Group_Cleanup(bpy.types.Operator):
    """Clean up duplicate groups and sync with mappings."""

    bl_idname = "chordsong.group_cleanup"
    bl_label = "Clean Up Groups"
    bl_description = "Remove duplicate groups and sync with mappings"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        """Execute group cleanup."""
        p = prefs(context)

        # Count duplicates before cleanup
        seen_names = set()
        duplicate_count = 0

        for grp in p.groups:
            name = grp.name.strip() if grp.name else ""
            if not name or name in seen_names:
                duplicate_count += 1
            else:
                seen_names.add(name)

        # Trigger sync which will remove duplicates
        p._sync_groups_from_mappings()  # pylint: disable=protected-access

        if duplicate_count > 0:
            self.report({"INFO"}, f"Removed {duplicate_count} duplicate group(s)")
        else:
            self.report({"INFO"}, "No duplicate groups found")

        from .common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}
