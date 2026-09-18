# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught
"""Where is this chord active? — one dialog for Global and per-context copies.

chordsong.mapping_contexts opens on a mapping and shows every context as a
toggle, pre-ticked where an identical copy of the chord already exists
(same chord, label, action — see core.chord_serialization.mapping_signature).
The ticked set is the chord's presence after OK:

  * tick a context      → a copy is created there
  * untick a context    → that copy is removed
  * Make Global         → one Global mapping replaces every copy

The original mapping is kept (re-contexted if its own context was unticked)
so its position in the list and its order index survive.
"""

import bpy  # type: ignore
from bpy.props import BoolProperty, EnumProperty, IntProperty  # type: ignore

from ..common import prefs, schedule_autosave_safe
from ...core.contexts import (
    ALL_CONTEXT,
    CONTEXTS,
    CONTEXT_TOKENS,
    context_chain,
    context_label,
    enum_items as _context_enum_items,
)
from ...core.chord_serialization import mapping_signature
from ...core.engine import get_str_attr

_CONTEXT_FLAG_ENUM_ITEMS = _context_enum_items(include_all=False, icons=True, flags=True)
_CONTEXT_GRID_COLUMNS = 3


def copy_mapping_fields(source, dest, context=None):
    """Copy every mapping field (operator chain, sub-items, script params)
    from ``source`` onto the freshly added ``dest``; ``context`` overrides
    the copied context token."""
    dest.enabled = getattr(source, "enabled", True)
    dest.chord = get_str_attr(source, "chord")
    dest.label = get_str_attr(source, "label")
    dest.icon = get_str_attr(source, "icon")
    dest.group = get_str_attr(source, "group")
    dest.context = context or getattr(source, "context", "VIEW_3D")
    dest.mapping_type = getattr(source, "mapping_type", "OPERATOR")
    dest.operator = get_str_attr(source, "operator")
    dest.python_file = get_str_attr(source, "python_file")
    dest.context_path = get_str_attr(source, "context_path")
    dest.call_context = getattr(source, "call_context", "EXEC_DEFAULT")
    dest.kwargs_json = get_str_attr(source, "kwargs_json")
    dest.property_value = get_str_attr(source, "property_value")
    dest.sync_toggles = bool(getattr(source, "sync_toggles", False))

    for src in getattr(source, "sub_operators", []) or []:
        dst = dest.sub_operators.add()
        dst.operator = get_str_attr(src, "operator")
        dst.call_context = getattr(src, "call_context", "EXEC_DEFAULT")
        dst.kwargs_json = get_str_attr(src, "kwargs_json")
    for src in getattr(source, "sub_items", []) or []:
        dst = dest.sub_items.add()
        dst.path = get_str_attr(src, "path")
        dst.value = get_str_attr(src, "value")
    for src in getattr(source, "script_params", []) or []:
        dst = dest.script_params.add()
        dst.value = get_str_attr(src, "value")


def _renumber(p):
    for i, m in enumerate(p.mappings):
        m.order_index = i


def identical_indices(p, idx):
    """Indices of every mapping identical to mappings[idx] (idx included),
    whatever their context."""
    signature = mapping_signature(p.mappings[idx])
    return [i for i, m in enumerate(p.mappings) if mapping_signature(m) == signature]


def inherits_from(token, selected):
    """True when `token` already runs a chord bound to one of `selected`
    because it inherits from it (Sequencer Preview from Video Sequencer)."""
    return any(parent in selected for parent in context_chain(token)[1:])


def inherited_targets(selected):
    """Contexts *outside* `selected` that already run its chords. Greyed out
    in the dialog: ticking one would only duplicate the chord into a
    conflict with the copy it already inherits."""
    return {c.token for c in CONTEXTS
            if c.token not in selected and inherits_from(c.token, selected)}


def redundant_targets(selected):
    """Contexts *inside* `selected` that another selected context already
    covers. Copying into them would duplicate the chord against its own
    parent, so they are dropped with a note."""
    return {t for t in selected if inherits_from(t, selected)}


def contexts_using_chord(p, chord, skip_indices=()):
    """Contexts that already bind `chord` to something, ignoring the rows in
    `skip_indices`. Used to warn instead of silently creating a duplicate."""
    chord = (chord or "").strip()
    if not chord:
        return set()
    skip = set(skip_indices)
    return {getattr(m, "context", "") for i, m in enumerate(p.mappings)
            if i not in skip and get_str_attr(m, "chord").strip() == chord}


class CHORDSONG_OT_Mapping_Contexts(bpy.types.Operator):
    """Choose the contexts this chord is active in: tick to add a copy, untick to remove one, or make it Global"""
    bl_idname = "chordsong.mapping_contexts"
    bl_label = "Chord Contexts"
    bl_options = {"INTERNAL", "UNDO"}

    index: IntProperty(default=-1)

    contexts: EnumProperty(
        name="Active in",
        description="Contexts where this chord exists after OK (pre-ticked where an identical copy already exists)",
        items=_CONTEXT_FLAG_ENUM_ITEMS,
        options={'ENUM_FLAG'},
        default=set(),
    )

    make_global: BoolProperty(
        name="Make Global",
        description="One Global mapping, active in every editor, replaces all copies of this chord",
        default=False,
    )

    def invoke(self, context, _event):
        p = prefs(context)
        idx = int(self.index)
        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}
        src = p.mappings[idx]
        present = {getattr(p.mappings[i], "context", "") for i in identical_indices(p, idx)}
        self.make_global = ALL_CONTEXT in present
        self.contexts = {c for c in present if c in CONTEXT_TOKENS}
        if not self.contexts and not self.make_global:
            own = getattr(src, "context", "")
            self.contexts = {own} if own in CONTEXT_TOKENS else set()
        return context.window_manager.invoke_props_dialog(self, width=520)

    def draw(self, context):
        p = prefs(context)
        layout = self.layout
        idx = int(self.index)
        if 0 <= idx < len(p.mappings):
            m = p.mappings[idx]
            label = get_str_attr(m, "label") or get_str_attr(m, "chord") or "chord"
            copies = len(identical_indices(p, idx))
            head = layout.row(align=True)
            head.label(text=f"\"{label}\" is active in:", icon='FILE_ALIAS')
            tail = head.row(align=True)
            tail.alignment = 'RIGHT'
            tail.enabled = False
            tail.label(text=f"{copies} cop{'y' if copies == 1 else 'ies'}")

        layout.prop(self, "make_global", text="Make Global (every editor)", icon='WORLD', toggle=True)
        inherited = inherited_targets(set(self.contexts))
        grid = layout.grid_flow(row_major=True, columns=_CONTEXT_GRID_COLUMNS, even_columns=True, align=True)
        grid.enabled = not self.make_global
        for ctx in CONTEXTS:
            cell = grid.row(align=True)
            # A context that inherits a ticked one already runs the chord;
            # ticking it would only duplicate it into a conflict.
            cell.enabled = ctx.token not in inherited
            cell.prop_enum(self, "contexts", ctx.token, icon=ctx.icon)

        note = layout.column(align=True)
        note.enabled = False
        if self.make_global:
            note.label(text="All copies are merged into one Global mapping.", icon='INFO')
        else:
            note.label(text="Ticked: a copy exists there. Unticked: that copy is removed.", icon='INFO')
            if inherited:
                names = ", ".join(sorted(context_label(t) for t in inherited))
                note.label(text=f"Greyed out, already inherited: {names}", icon='BLANK1')

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        idx = int(self.index)
        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        same = identical_indices(p, idx)
        signature = mapping_signature(p.mappings[idx])

        if self.make_global:
            p.mappings[idx].context = ALL_CONTEXT
            removed = 0
            for i in sorted(same, reverse=True):
                if i != idx:
                    p.mappings.remove(i)
                    removed += 1
            _renumber(p)
            self._finish(p)
            self.report({"INFO"}, "Made Global" + (f", merged {removed} cop{'y' if removed == 1 else 'ies'}" if removed else ""))
            return {"FINISHED"}

        targets = [c for c in CONTEXT_TOKENS if c in self.contexts]
        if not targets:
            # Cancelling would be the destructive reading of "no contexts":
            # it would leave the chord exactly where it was while looking
            # like the dialog did something. Say so and change nothing.
            self.report({"WARNING"}, "No context ticked - the chord was left unchanged")
            return {"CANCELLED"}
        # Never copy into a context that already inherits another target.
        skipped_inherited = sorted(redundant_targets(set(targets)))
        targets = [t for t in targets if t not in skipped_inherited]

        present = {}
        for i in same:
            present.setdefault(getattr(p.mappings[i], "context", ""), i)
        to_add = [t for t in targets if t not in present]
        to_remove = [i for i in same if getattr(p.mappings[i], "context", "") not in targets]

        # Keep the original alive: if its own context was unticked, re-context
        # it to the first new target instead of deleting it.
        if idx in to_remove:
            to_remove.remove(idx)
            if to_add:
                p.mappings[idx].context = to_add.pop(0)
            else:
                # Every target already has a copy elsewhere; the original is
                # redundant, so it goes too.
                to_remove.append(idx)

        for i in sorted(to_remove, reverse=True):
            p.mappings.remove(i)

        # Re-locate the template (its index may have shifted) and add copies
        # right after it.
        template_idx = next(
            (i for i, m in enumerate(p.mappings)
             if getattr(m, "context", "") in targets and mapping_signature(m) == signature), None)
        if template_idx is None and to_add:
            self.report({"WARNING"}, "Could not find a template mapping to copy")
            return {"CANCELLED"}
        # Warn before copying the chord into a context where that sequence
        # is already bound to something else; the alternative is a silent
        # duplicate the user only meets later as a red row.
        chord = get_str_attr(p.mappings[template_idx], "chord") if template_idx is not None else ""
        clashing = sorted(set(to_add) & contexts_using_chord(p, chord, same))
        if clashing:
            self.report({"WARNING"}, "Chord already used in "
                        + ", ".join(context_label(c) for c in clashing))

        for offset, ctx in enumerate(to_add, start=1):
            new_m = p.mappings.add()
            copy_mapping_fields(p.mappings[template_idx], new_m, context=ctx)
            new_index = len(p.mappings) - 1
            target_index = template_idx + offset
            if target_index < new_index:
                p.mappings.move(new_index, target_index)

        _renumber(p)
        self._finish(p)
        added, removed = len(to_add), len(to_remove)
        parts = []
        if added:
            parts.append(f"copied to {added} context{'s' if added != 1 else ''}")
        if removed:
            parts.append(f"removed from {removed}")
        if skipped_inherited:
            parts.append("skipped " + ", ".join(context_label(c) for c in skipped_inherited)
                         + " (already inherited)")
        self.report({"INFO"}, ("Chord " + ", ".join(parts)) if parts else "No change")
        return {"FINISHED"}

    @staticmethod
    def _finish(p):
        from ...ui.overlay import clear_overlay_cache
        clear_overlay_cache()
        schedule_autosave_safe(p, delay_s=5.0)


__all__ = ["CHORDSONG_OT_Mapping_Contexts", "copy_mapping_fields", "identical_indices", "context_label"]
