"""Group cleanup operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel,relative-beyond-top-level

import bpy

from ..common import prefs

class CHORDSONG_OT_Group_Cleanup(bpy.types.Operator):
    """Clean up duplicate groups, normalize order indices, and sync with mappings."""

    bl_idname = "chordsong.group_cleanup"
    bl_label = "Clean Up Groups"
    bl_description = "Remove duplicate groups, normalize order indices, and sync with mappings"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        """Execute group cleanup."""
        p = prefs(context)

        # 1. Identify used group names
        used_names = set()
        for m in p.mappings:
            name = (getattr(m, "group", "") or "").strip()
            if name:
                used_names.add(name)

        # 2. Categorize groups for detailed reporting
        empty_groups = []
        duplicate_groups = []
        seen_names = set()
        
        for grp in p.groups:
            name = grp.name.strip() if grp.name else ""
            if not name:
                # Completely empty name property
                empty_groups.append("(nameless)")
                continue

            if name in seen_names:
                duplicate_groups.append(name)
            elif name not in used_names:
                empty_groups.append(name)
            
            seen_names.add(name)

        # 3. Normalize order indices for all mappings + group indices
        from ...core.config_io import _normalize_order_indices, _normalize_group_indices
        _normalize_order_indices(p.mappings)
        _normalize_group_indices(p.groups)

        # 4. Trigger the actual sync via a delayed timer for stability
        p.sync_groups_delayed(remove_unused=True)

        # 5. Construct detailed report
        messages = []
        if duplicate_groups:
            messages.append(f"Merged duplicates: {', '.join(set(duplicate_groups))}")
        if empty_groups:
            messages.append(f"Removed empty: {', '.join(set(empty_groups))}")

        if messages:
            report_str = " | ".join(messages)
            self.report({"INFO"}, report_str)
            print(f"CHORD SONG CLEANUP: {report_str}")
        else:
            self.report({"INFO"}, "Groups cleaned up")

        from ..common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        return {"FINISHED"}
