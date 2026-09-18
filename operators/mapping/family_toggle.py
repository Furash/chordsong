# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught
"""Roll an editor family open/closed in the Mappings tab context selector.

Open families are stored as a comma-separated list of space types in
prefs.open_editor_families so the layout survives restarts. The family
holding the selected context is always shown open (see mappings_tab).
"""

import bpy  # type: ignore
from bpy.props import StringProperty  # type: ignore

from ..common import prefs


def open_families(p):
    """Set of space types whose rollout is open."""
    raw = getattr(p, "open_editor_families", "") or ""
    return {s.strip() for s in raw.split(",") if s.strip()}


def leader_override_spaces(p):
    """Set of space types that have their own leader key (authoritative —
    see prefs.leader_key_overrides)."""
    raw = getattr(p, "leader_key_overrides", "") or ""
    return {s.strip() for s in raw.split(",") if s.strip()}


def set_leader_override_spaces(p, spaces):
    p.leader_key_overrides = ",".join(sorted(spaces))


class CHORDSONG_OT_Leader_Override_Toggle(bpy.types.Operator):
    """Give this editor its own leader key, or reset it to the default key"""
    bl_idname = "chordsong.leader_override_toggle"
    bl_label = "Leader Key Override"
    bl_options = {"INTERNAL"}

    space_type: StringProperty(default="")

    def execute(self, context):
        from ...core.contexts import LEADER_KEYMAPS
        from ...ui.keymap import MASTER_KEYMAP_NAME, copy_leader_event, find_leader_kmi

        p = prefs(context)
        km_name = {space: name for name, space in LEADER_KEYMAPS}.get(self.space_type)
        if not km_name or km_name == MASTER_KEYMAP_NAME:
            return {"CANCELLED"}
        _, master = find_leader_kmi(MASTER_KEYMAP_NAME)
        _, kmi = find_leader_kmi(km_name)
        if master is None or kmi is None:
            self.report({"WARNING"}, "Leader keymap not found")
            return {"CANCELLED"}

        spaces = leader_override_spaces(p)
        if self.space_type in spaces:
            # Reset: the whole binding goes back to the default, modifiers
            # included — copying only the key type would strand a Ctrl.
            copy_leader_event(kmi, master)
            spaces.discard(self.space_type)
            self.report({"INFO"}, "Leader key reset to the default")
        else:
            spaces.add(self.space_type)
        set_leader_override_spaces(p, spaces)
        return {"FINISHED"}


class CHORDSONG_OT_Context_Select(bpy.types.Operator):
    """Show this editor's chords"""
    bl_idname = "chordsong.context_select"
    bl_label = "Select Context"
    bl_options = {"INTERNAL"}

    token: StringProperty(default="")

    def execute(self, context):
        p = prefs(context)
        if not self.token:
            return {"CANCELLED"}
        try:
            p.mapping_context_tab = self.token
        except TypeError:
            self.report({"WARNING"}, f"Unknown context {self.token}")
            return {"CANCELLED"}
        return {"FINISHED"}


class CHORDSONG_OT_Family_Toggle(bpy.types.Operator):
    """Roll this editor's contexts open or closed"""
    bl_idname = "chordsong.family_toggle"
    bl_label = "Toggle Editor Rollout"
    bl_options = {"INTERNAL"}

    space_type: StringProperty(default="")

    def execute(self, context):
        p = prefs(context)
        if not self.space_type:
            return {"CANCELLED"}
        if self.space_type == "*":
            # Collapse every rollout — selecting contexts opens them, so
            # they accumulate and there has to be a way back.
            p.open_editor_families = ""
            return {"FINISHED"}
        opened = open_families(p)
        if self.space_type in opened:
            opened.discard(self.space_type)
        else:
            opened.add(self.space_type)
        p.open_editor_families = ",".join(sorted(opened))
        return {"FINISHED"}
