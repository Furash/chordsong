"""Operators for the statistics tab: refresh, export, reload, reset,
blacklist management, and converting a tracked operator into a chord mapping."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import bpy
from bpy.types import Operator

from ..core import stats_manager, stats_store
from ..core.contexts import DEFAULT_CONTEXT, enum_items as _context_enum_items
from ..core.engine import humanize_chord, split_chord, tokens_match
from ..utils.addon_package import addon_root_package
from .common import prefs, schedule_autosave_safe
from .context_menu.extractors import detect_editor_context
from .context_menu.suggester import suggest_chord

# Global included: a chord converted from the stats list is often one the
# user wants everywhere, and this was the only picker that could not.
_CONTEXT_ENUM_ITEMS = _context_enum_items(include_all=True, icons=True)
# Matches the other context pickers; one row of 25 was unreadable.
_CONTEXT_GRID_COLUMNS = 3


def _prefs_from_context(context):
    return context.preferences.addons[addon_root_package(__package__)].preferences


def _base_key(tokens):
    """The chord's tokens with modifiers stripped.

    `tokens_match` requires the base characters to be equal before it looks
    at modifiers, so two chords can only match if this key matches — which
    makes it a safe index for finding candidates without scanning the whole
    mapping list per row.
    """
    from ..core.engine import _get_token_parts
    return tuple(_get_token_parts(t)[1] for t in tokens)


def _mappings_digest(p):
    """Everything about the mappings that the stats list displays.

    Plain attribute reads, no chord parsing: this runs on every redraw just
    to decide whether the list needs rebuilding, so it has to stay cheap.
    """
    return tuple(
        ((m.chord or "").strip(), m.label or "", m.group or "",
         getattr(m, "mapping_type", "OPERATOR"),
         (getattr(m, "python_file", "") or "").strip(),
         (getattr(m, "context_path", "") or "").strip())
        for m in p.mappings
    )


def _mapping_indexes(p):
    """The three lookups the stats list needs, in one pass.

    Built per rebuild rather than per row: matching each row back to a
    mapping used to rescan and re-split the whole mapping list, which is
    O(rows x mappings) of string work on every redraw.
    """
    import os

    by_base = {}      # base-token key -> [(tokens, mapping)]
    by_script = {}    # script file name -> mapping
    by_path = {}      # context path -> mapping

    for m in p.mappings:
        chord = (m.chord or "").strip()
        mapping_type = getattr(m, "mapping_type", "OPERATOR")
        python_file = (getattr(m, "python_file", "") or "").strip()
        context_path = (getattr(m, "context_path", "") or "").strip()

        if chord:
            toks = split_chord(chord)
            if toks:
                by_base.setdefault(_base_key(toks), []).append((toks, m))
        if python_file:
            by_script.setdefault(os.path.basename(python_file), m)
        if mapping_type in ("CONTEXT_PROPERTY", "CONTEXT_TOGGLE") and context_path:
            by_path.setdefault(context_path, m)

    return by_base, by_script, by_path


def _find_mapping_for_script(by_script, script_name):
    """The mapping whose python_file matches a recorded script file name."""
    return by_script.get(script_name)


def _find_mapping_for_property(by_path, path):
    """The CONTEXT_PROPERTY/TOGGLE mapping whose context_path matches."""
    return by_path.get(path)


def _find_mapping_for_chord(by_base, chord_str):
    """The mapping whose chord matches a recorded chord token string."""
    key_tokens = split_chord(chord_str)
    if not key_tokens:
        return None
    for m_tokens, m in by_base.get(_base_key(key_tokens), ()):
        if len(m_tokens) == len(key_tokens) and all(
            tokens_match(mt, kt) for mt, kt in zip(m_tokens, key_tokens)
        ):
            return m
    return None


# What the built list depends on. Rebuilding is expensive (it clears and
# refills an RNA collection), and the Statistics tab asks for it on every
# redraw — which is every frame while the preferences window is dragged.
_last_list_signature = None


def invalidate_stats_ui():
    """Force the next refresh_stats_ui to rebuild."""
    global _last_list_signature  # pylint: disable=global-statement
    _last_list_signature = None


def refresh_stats_ui(p, force=False):
    """Rebuild the stats UI collection from current counts, minus blacklist.

    Returns True when the collection is up to date — including the case
    where nothing changed and the existing rows were kept.
    """
    global _last_list_signature  # pylint: disable=global-statement
    try:
        signature = (
            stats_manager.revision(),
            getattr(p, "stats_blacklist", "") or "",
            bool(getattr(p, "stats_sort_by_usage", False)),
            _mappings_digest(p),
        )
        if not force and signature == _last_list_signature and len(p.stats_collection):
            return True

        by_base, by_script, by_path = _mapping_indexes(p)
        p.stats_collection.clear()
        blacklist = stats_store.parse_blacklist(p.stats_blacklist)

        rows = []
        for category in stats_store.CATEGORIES:
            for name, count in stats_manager.get_stats(category).items():
                if stats_store.blacklist_key(category, name) not in blacklist:
                    rows.append((category, name, count))

        if p.stats_sort_by_usage:
            rows.sort(key=lambda r: (-r[2], r[0], r[1]))
        else:
            rows.sort(key=lambda r: (r[0], r[1]))

        for category, name, count in rows:
            item = p.stats_collection.add()
            item.category = category
            item.name = name
            item.count = count
            if category == "chords":
                mapping = _find_mapping_for_chord(by_base, name)
            elif category == "scripts":
                mapping = _find_mapping_for_script(by_script, name)
            elif category == "properties":
                mapping = _find_mapping_for_property(by_path, name)
            else:
                mapping = None
            if mapping:
                item.group = mapping.group or ""
                item.label = mapping.label or ""

        _last_list_signature = signature
        return True
    except Exception:
        _last_list_signature = None
        return False


class CHORDSONG_OT_Stats_Refresh(Operator):
    """Refresh the statistics display"""
    bl_idname = "chordsong.stats_refresh"
    bl_label = "Refresh Statistics"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        if not refresh_stats_ui(_prefs_from_context(context), force=True):
            self.report({'ERROR'}, "Failed to refresh statistics")
            return {'CANCELLED'}
        return {'FINISHED'}


class CHORDSONG_OT_Stats_Export(Operator):
    """Write current statistics to the stats JSON file"""
    bl_idname = "chordsong.stats_export"
    bl_label = "Export Statistics"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        path = stats_manager.get_stats_file_path()
        if not path:
            self.report({'ERROR'}, "Cannot determine stats file path")
            return {'CANCELLED'}
        if stats_manager.write_current_to_file(path):
            self.report({'INFO'}, f"Statistics saved to {path}")
            return {'FINISHED'}
        self.report({'ERROR'}, "Failed to write statistics to file")
        return {'CANCELLED'}


class CHORDSONG_OT_Stats_Reload(Operator):
    """Reload statistics from the stats file, discarding unsaved counts"""
    bl_idname = "chordsong.stats_reload"
    bl_label = "Reload from JSON"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        p = _prefs_from_context(context)
        if stats_manager.reload_from_path(stats_manager.get_stats_file_path()):
            refresh_stats_ui(p)
            self.report({'INFO'}, "Statistics reloaded from JSON")
            return {'FINISHED'}
        self.report({'WARNING'}, "No stats file found or could not load")
        return {'CANCELLED'}


class CHORDSONG_OT_Stats_Reset(Operator):
    """Delete all recorded statistics (memory and file)"""
    bl_idname = "chordsong.stats_reset"
    bl_label = "Reset Statistics"
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        stats_manager.clear_all()
        refresh_stats_ui(_prefs_from_context(context))
        self.report({'INFO'}, "Statistics reset")
        return {'FINISHED'}


class CHORDSONG_OT_Stats_Blacklist(Operator):
    """Hide items from statistics: toggle, edit, or clear the blacklist"""
    bl_idname = "chordsong.stats_blacklist"
    bl_label = "Blacklist Manager"
    bl_options = {'INTERNAL'}

    action: bpy.props.EnumProperty(
        name="Action",
        items=[
            ('TOGGLE', "Toggle", "Toggle blacklist status for an item"),
            ('EDIT', "Edit", "Open blacklist editor dialog"),
            ('REMOVE', "Remove", "Remove item from blacklist"),
            ('CLEAR', "Clear", "Clear all blacklisted items"),
        ],
        default='TOGGLE',
    )
    category: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(default="")

    def invoke(self, context, event):
        if self.action == 'EDIT':
            return context.window_manager.invoke_props_dialog(self, width=500)
        return self.execute(context)

    def execute(self, context):
        p = _prefs_from_context(context)
        blacklist = stats_store.parse_blacklist(p.stats_blacklist)

        if self.action == 'TOGGLE':
            if self.category and self.name:
                category, name = self.category, self.name
            else:
                index = p.stats_collection_index
                if index < 0 or index >= len(p.stats_collection):
                    self.report({'WARNING'}, "No item selected")
                    return {'CANCELLED'}
                item = p.stats_collection[index]
                category, name = item.category, item.name
            key = stats_store.blacklist_key(category, name)
            if key in blacklist:
                blacklist.discard(key)
            else:
                blacklist.add(key)
            # Remember the toggled row's position: the rebuild below replaces
            # the collection, and template_list auto-scrolls to wherever the
            # stale active index ends up. Re-anchoring it at the same spot
            # keeps the view where the user was working.
            pos = next(
                (i for i, it in enumerate(p.stats_collection)
                 if it.category == category and it.name == name),
                p.stats_collection_index,
            )
            p.stats_blacklist = stats_store.dump_blacklist(blacklist)
            stats_manager.mark_dirty()
            refresh_stats_ui(p)
            p.stats_collection_index = max(0, min(pos, len(p.stats_collection) - 1))

        elif self.action == 'REMOVE':
            if not self.category or not self.name:
                self.report({'WARNING'}, "Category and name required")
                return {'CANCELLED'}
            blacklist.discard(stats_store.blacklist_key(self.category, self.name))
            p.stats_blacklist = stats_store.dump_blacklist(blacklist)
            stats_manager.mark_dirty()
            refresh_stats_ui(p)
            # Reopen the editor dialog so removal feels in-place
            bpy.ops.chordsong.stats_blacklist('INVOKE_DEFAULT', action='EDIT')

        elif self.action == 'CLEAR':
            p.stats_blacklist = stats_store.dump_blacklist(set())
            stats_manager.mark_dirty()
            refresh_stats_ui(p)
            self.report({'INFO'}, "Blacklist cleared")

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        p = _prefs_from_context(context)
        blacklist = stats_store.parse_blacklist(p.stats_blacklist)

        box = layout.box()
        if not blacklist:
            box.row().label(text="No items in blacklist", icon='INFO')
            return

        box.row().label(text=f"Blacklisted Items ({len(blacklist)}):", icon='CHECKBOX_HLT')
        for key in sorted(blacklist):
            category, _, name = key.partition(':')
            row = box.row(align=True)
            icon = {'chords': 'EVENT_SPACE', 'scripts': 'FILE_SCRIPT', 'properties': 'RNA'}.get(category, 'SETTINGS')
            row.label(text=category.capitalize(), icon=icon)
            row.separator()
            row.label(text=name)
            row.separator()
            op = row.operator("chordsong.stats_blacklist", text="Remove", icon='X')
            op.action = 'REMOVE'
            op.category = category
            op.name = name

        row = box.row()
        row.scale_y = 1.3
        op = row.operator("chordsong.stats_blacklist", text="Clear All Blacklist", icon='TRASH')
        op.action = 'CLEAR'


class CHORDSONG_OT_Stats_Convert_To_Chord(Operator):
    """Create a new chord mapping for a tracked operator or property"""
    bl_idname = "chordsong.stats_convert_to_chord"
    bl_label = "Convert to Chord"
    bl_options = {'INTERNAL'}

    stats_name: bpy.props.StringProperty(default="")
    stats_category: bpy.props.StringProperty(default="operators")

    property_value: bpy.props.StringProperty(name="Value", default="")
    operator: bpy.props.StringProperty(name="Operator", default="")
    chord: bpy.props.StringProperty(name="Chord", default="")
    name: bpy.props.StringProperty(name="Label", default="")
    group: bpy.props.StringProperty(name="Group", default="")
    kwargs: bpy.props.StringProperty(name="Parameters", default="")
    editor_context: bpy.props.EnumProperty(
        name="Editor Context",
        items=_CONTEXT_ENUM_ITEMS,
        default=DEFAULT_CONTEXT,
    )

    def invoke(self, context, _event):
        name = (self.stats_name or "").strip()
        self.kwargs = ""
        self.chord = ""
        if self.stats_category == "properties":
            # name is a context path like "space_data.clip_end"
            self.operator = name
            from ..core.stats_manager import get_last_property_value
            self.property_value = get_last_property_value(name)
            parts = name.split(".")
            self.group = parts[0].replace("_", " ").title() if parts else ""
            self.name = parts[-1].replace("_", " ").title() if parts else ""
        else:
            # Stats store operator idnames as "module.op"; mappings use the same form.
            self.operator = name
            module, _, op_name = name.partition(".")
            self.group = module.replace("_", " ").title() if module else ""
            self.name = op_name.replace("_", " ").title() if op_name else ""
        self.editor_context = detect_editor_context(context, self.operator, self.kwargs)
        self.chord = suggest_chord(self.group, self.name)
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, _context):
        col = self.layout.column(align=True)
        if self.stats_category == "properties":
            col.label(text=f"Property: {self.operator}", icon="RNA")
        else:
            col.label(text=f"Operator: {self.operator}", icon="SETTINGS")
        col.separator()
        col.label(text="Enter Chord:")
        col.prop(self, "chord", text="")
        col.separator()
        col.label(text="Editor Context:")
        grid = col.grid_flow(row_major=True, columns=_CONTEXT_GRID_COLUMNS,
                             even_columns=True, align=True)
        grid.prop(self, "editor_context", expand=True)
        col.separator()
        col.prop(self, "name", text="Label")
        col.prop(self, "group", text="Group")
        if self.stats_category == "properties":
            col.prop(self, "property_value", text="Value")
        else:
            col.prop(self, "kwargs", text="Parameters")

    def execute(self, context):
        p = prefs(context)
        if not self.chord:
            self.report({'WARNING'}, "Please enter a chord")
            return {"CANCELLED"}
        if not self.operator:
            self.report({'WARNING'}, "Nothing to convert")
            return {"CANCELLED"}

        m = p.mappings.add()
        m.enabled = True
        m.chord = self.chord
        m.label = self.name or "New Chord"
        m.group = self.group or ""
        m.context = self.editor_context
        if self.stats_category == "properties":
            m.mapping_type = "CONTEXT_PROPERTY"
            m.context_path = self.operator
            m.property_value = self.property_value
        else:
            m.operator = self.operator
            m.call_context = "INVOKE_DEFAULT"
            m.kwargs_json = self.kwargs or ""
            m.mapping_type = "OPERATOR"

        last_index = len(p.mappings) - 1
        if last_index > 0:
            p.mappings.move(last_index, 0)

        schedule_autosave_safe(p, delay_s=5.0)
        p.prefs_tab = "MAPPINGS"
        self.report({'INFO'}, f"Added chord '{self.chord}' for: {self.operator}")
        return {"FINISHED"}


def chord_display_text(chord_str: str) -> str:
    """Readable form of a recorded chord key for the stats list."""
    return humanize_chord(split_chord(chord_str))
