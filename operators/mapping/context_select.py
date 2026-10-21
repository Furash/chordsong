# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught
"""Operators behind the Mappings-tab context selector: pick the context
whose chords the tab lists, and give an editor its own leader key."""

import bpy  # type: ignore
from bpy.props import StringProperty  # type: ignore

from ..common import prefs


def leader_override_spaces(p):
    """Set of space types that have their own leader key (authoritative —
    see prefs.leader_key_overrides)."""
    raw = getattr(p, "leader_key_overrides", "") or ""
    return {s.strip() for s in raw.split(",") if s.strip()}


def set_leader_override_spaces(p, spaces):
    p.leader_key_overrides = ",".join(sorted(spaces))


class CHORDSONG_OT_Leader_Default_Key(bpy.types.Operator):
    """Holds the default leader key. Bound by an inactive keymap item that
    exists only to be edited in the preferences; never meant to run."""
    bl_idname = "chordsong.leader_default_key"
    bl_label = "Leader Key (default)"
    bl_options = {"INTERNAL"}

    def execute(self, context):
        # Should the item ever be switched on, let the key through.
        return {"PASS_THROUGH"}


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
        if not km_name:
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

    @classmethod
    def description(cls, context, properties):
        # The Mappings-tab chips show only an icon and a count, so the
        # tooltip has to carry the context's name.
        from ...core.contexts import ALL_CONTEXT, CONTEXT_BY_TOKEN
        token = getattr(properties, "token", "")
        if token == ALL_CONTEXT:
            return "Global: chords that run in every editor"
        ctx = CONTEXT_BY_TOKEN.get(token)
        if ctx is None:
            return "Show this editor's chords"
        return f"{ctx.label}: {ctx.description}"

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
