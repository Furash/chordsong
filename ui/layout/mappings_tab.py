"""
Mappings tab for addon preferences.

Layout (two fixed columns; every row is [arrow cell][control ...]):
  ┌ Leader Key (default)  [Space Bar]        ┐ ┌ Multi-Toggle Modifier  [Ctrl]     ┐
  └──────────────────────────────────────────┘ └───────────────────────────────────┘
  ┌   🌐 Global · 18                          ┐ ┌ ▸ Movie Clip                      ┐
  └──────────────────────────────────────────┘ └───────────────────────────────────┘
  ┌ ▾ 3D View · 114                          ┐ ┌ ▾ Dope Sheet · 3                  ┐
  │   Leader Key          [Space Bar]        │ │   Leader Key        [Tab]       ↶ │
  │   [Object · 84       ][Edit · 30       ] │ │   [Dope Sheet · 3  ][Timeline    ] │
  │   [Sculpt            ][Paint           ] │ └───────────────────────────────────┘
  │   [Pose              ][                ] │  …
  └──────────────────────────────────────────┘
  [Add Chord] [Conflicts] [Add Group] …
  [Search…]                                              [Copy] [Paste]
  ▾ Group … mapping rows …
Rollouts per editor family (core.contexts.EDITOR_FAMILIES); the family of
the selected context opens on selection; arrow or header re-click collapses it. The default leader key is the 3D View
keymap and propagates to editors that follow it; the key cell at the end of
an editor row gives that editor its own key (⧉ Override, then field + ↶ reset).
"""

from ...core.contexts import (
    ALL_CONTEXT,
    DEFAULT_CONTEXT,
    EDITOR_FAMILIES,
    LEADER_KEYMAPS,
    context_chain,
    context_label,
    context_short_label,
    contexts_in_group,
    contexts_overlap,
    family_contexts,
    group_captions,
)
from ...core.engine import get_str_attr, mapping_matches_search
from ..keymap import (
    MASTER_KEYMAP_NAME,
    event_signature,
    find_leader_kmi,
    leader_event,
    leader_overrides,
    schedule_master_sync,
)
from ...core.conflicts import conflict_map, conflicts_with_any, contexts_with_conflicts
from .mapping_item import draw_mapping_item

# Context rollouts flow into two columns when the preferences region is at
# least this wide (pixels); one column below.
_ROLLOUT_TWO_COLUMN_MIN_PX = 1100
# Row grammar [arrow cell][control]: fixed arrow-cell width so every control
# starts at the same x, and a fixed label cell for "Leader Key" / "Multi-Toggle
# Modifier" lines so their fields line up too.
_ROLLOUT_ARROW_UNITS_X = 1.1
_ROLLOUT_LABEL_UNITS_X = 9.0
_ROLLOUT_COLUMN_GAP = 1.0
# Mode buttons per body row; a short last row is padded so widths match.
_ROLLOUT_MODES_PER_ROW = 2
# The body's "Leader Key" row is split like a mode row: label on the left,
# key cell (field + Override/reset icon) on the right.
_ROLLOUT_NAME_SHARE = 1.0 - 1.0 / _ROLLOUT_MODES_PER_ROW
# Sentinel space type: chordsong.family_toggle closes every rollout.
_COLLAPSE_ALL = "*"
# Leader keymap name per editor family (space type).
_KEYMAP_BY_SPACE = {space: name for name, space in LEADER_KEYMAPS}

# Shared with the search overlay; lives in core.engine (bpy-free, testable).
_matches_search = mapping_matches_search


def draw_mappings_tab(prefs, context, layout):
    """Draw the Mappings tab content."""
    root = layout.column()

    # One conflict picture for the whole draw. The preferences region
    # redraws every frame while the window is dragged, so this must be
    # built once and handed around, never re-derived per row.
    conflicts = conflict_map(prefs.mappings)

    _draw_context_rollouts(prefs, context, root, conflicts)
    root.separator()
    col = root.column()

    # Action bar
    row = col.row(align=True)
    row.scale_y = 1.5
    op = row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    op.context = prefs.mapping_context_tab
    row.separator()
    op = row.operator("chordsong.check_conflicts", text="Check for Conflicts", icon='ERROR')
    row.separator()
    op = row.operator("chordsong.group_add", text="Add New Group", icon="ADD")
    op.name = "New Group"
    row.separator()
    row.operator("chordsong.group_cleanup", text="", icon="BRUSH_DATA")
    row.separator()
    row.operator("chordsong.group_fold_all", text="", icon="TRIA_UP_BAR")
    row.separator()
    row.operator("chordsong.group_unfold_all", text="", icon="TRIA_DOWN_BAR")

    col.separator()

    # Search box and Copy/Paste/Selection bar
    search_main_row = col.row(align=True)
    search_split = search_main_row.split(factor=0.75, align=True)

    # Left side: Search bar
    search_row = search_split.row(align=True)
    search_row.scale_y = 1.3
    search_row.operator("chordsong.mapping_fold_all", text="", icon="TRIA_UP_BAR", emboss=False)
    search_row.separator()
    search_row.operator("chordsong.mapping_unfold_all", text="", icon="TRIA_DOWN_BAR", emboss=False)
    search_row.separator()
    search_row.prop(prefs, "chord_search", text="", icon="VIEWZOOM", placeholder="Search... (c: chords  l: labels  o: operators  p: properties  t: toggles  s: scripts)")
    if prefs.chord_search:
        search_row.operator("chordsong.clear_search", text="", icon="X", emboss=False)

    search_row.separator()
    search_row.separator()
    search_row.operator("chordsong.clear_operator_cache", text="", icon="FILE_REFRESH", emboss=False)
    search_row.separator()

    # Right side: Copy/Paste/Selection buttons
    button_row = search_split.row(align=True)
    button_row.scale_y = 1.3

    # Copy button changes appearance based on selection mode
    copy_row = button_row.row(align=True)
    if prefs.selection_mode:
        copy_row.alert = True
    copy_row.operator("chordsong.mapping_copy",
                      text="Copy selected" if prefs.selection_mode else "Copy Start",
                      icon="CHECKBOX_HLT" if prefs.selection_mode else "COPYDOWN")

    button_row.separator()

    # Paste button becomes Deselect All during selection mode
    if prefs.selection_mode:
        button_row.operator("chordsong.mapping_deselect_all", text="Deselect All", icon="CHECKBOX_DEHLT")
    else:
        button_row.operator("chordsong.mapping_paste", text="Paste", icon="PASTEDOWN")

    col.separator()

    # Filter mappings by selected context tab and search query. Global
    # (ALL) chords are managed only in the Global tab; an editor tab lists
    # its own mappings and links to the Global tab instead of repeating them.
    #
    # Two exceptions bring *foreign* mappings in as read-only rows:
    #   - a search is active on an editor tab: Global chords that match are
    #     listed too, so a search finds every chord active in that editor;
    #   - a conflict crosses the Global boundary: the other party is listed
    #     next to the chord it clashes with, so a red chord never points at
    #     something invisible.
    current_context = prefs.mapping_context_tab
    search_query = (prefs.chord_search or "").strip().lower()
    is_global_tab = current_context == ALL_CONTEXT

    own_indices = {i for i, m in enumerate(prefs.mappings)
                   if (getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT) == current_context}

    # Contexts whose chords are also active in this tab: parent editor
    # contexts (3D View for Sculpt, Sequencer for its Preview, ...) and
    # Global. Counted for the "also active here" links; listed read-only
    # only when they clash or match a search.
    inherited_sources = [] if is_global_tab else context_chain(current_context)[1:] + [ALL_CONTEXT]
    inherited_counts = {tok: 0 for tok in inherited_sources}

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        mapping_context = getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT
        readonly = False
        if mapping_context != current_context:
            if mapping_context in inherited_counts:
                # Counted after the search filter below, so the link never
                # advertises more rows than the list shows.
                if not (search_query or conflicts_with_any(conflicts, idx, own_indices)):
                    inherited_counts[mapping_context] += 1
                    continue
            elif contexts_overlap(mapping_context, current_context):
                # Mode context under this editor, or an editor chord seen
                # from Global: only when it clashes with one of ours
                if not conflicts_with_any(conflicts, idx, own_indices):
                    continue
            else:
                continue
            readonly = True

        # Apply search filter
        if not _matches_search(m, search_query):
            continue

        if readonly and mapping_context in inherited_counts:
            inherited_counts[mapping_context] += 1

        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m, readonly))

    if any(inherited_counts.values()):
        note = col.row(align=True)
        note.alignment = 'LEFT'
        note.label(text="Also active here:")
        for tok, n in inherited_counts.items():
            if n:
                note.prop_enum(
                    prefs, "mapping_context_tab", tok,
                    text=f"{context_label(tok)} ({n})",
                    icon='WORLD' if tok == ALL_CONTEXT else 'NONE',
                )
        col.separator()

    # Build group order from prefs.groups collection (user-defined order)
    # Groups in the collection come first (in order), then any remaining groups alphabetically
    group_order = []
    for grp in prefs.groups:
        if grp.name in groups:
            group_order.append(grp.name)
    # Add any groups not in the collection (e.g., "Ungrouped" or orphaned groups)
    remaining = [g for g in groups.keys() if g not in group_order]
    # Sort remaining: "Ungrouped" first, then alphabetically
    remaining.sort(key=lambda s: (s != "Ungrouped", s.lower()))
    group_order = remaining + group_order  # Ungrouped first, then user-ordered groups

    if not groups:
        hint = col.column(align=True)
        hint.alignment = 'CENTER'
        hint.enabled = False
        if search_query:
            # The context may be full; the search simply matched nothing.
            hint.label(text=f'No chord here matches "{prefs.chord_search}".', icon='VIEWZOOM')
        else:
            hint.label(text="No mappings in this context yet — use Add New Chord, "
                            "or right-click any button in Blender.")
            # A zero count reads as "Chord Song does nothing here"; say what
            # is actually active before the user rebuilds it by hand.
            inherited_total = sum(inherited_counts.values())
            if inherited_total:
                names = ", ".join(context_label(t) for t, n in inherited_counts.items() if n)
                hint.label(text=f"{inherited_total} chord(s) from {names} are active here.")

    # Draw grouped UI boxes
    for group_name in group_order:
        items = groups[group_name]
        # Keep items in the order they appear in prefs.mappings (manual ordering)
        # Don't sort automatically - users can use the sort button if they want alphabetical order

        is_expanded, expand_data, expand_prop = _get_group_expansion_state(prefs, group_name)

        # Auto-expand groups when search is active
        if search_query:
            is_expanded = True

        # Check if any mapping in this group has conflicts
        group_has_conflicts = any(idx in conflicts for idx, _m, _ro in items)

        # Foldable header row
        header = col.row(align=True)

        # Split: Label (Left) | Buttons (Right)
        split = header.split(factor=0.6)

        # Left side: Expansion + Group Name
        row_left = split.row(align=True)
        if expand_data and expand_prop:
            row_left.prop(
                expand_data, expand_prop,
                icon="TRIA_DOWN" if is_expanded else "TRIA_RIGHT",
                text="",
                emboss=False,
            )

        # Show group icon if available
        group_icon = ""
        if group_name != "Ungrouped":
            for grp in prefs.groups:
                if grp.name == group_name:
                    group_icon = grp.icon
                    break

        # Show conflict indicator if group has conflicted chords
        if group_has_conflicts:
            row_left.alert = True
            if group_icon:
                row_left.label(text=f"{group_icon} {group_name}", icon="ERROR")
            else:
                row_left.label(text=f"{group_name}", icon="ERROR")
        else:
            if group_icon:
                row_left.label(text=f"{group_icon} {group_name}")
            else:
                row_left.label(text=f"{group_name}")

        # Right side: Buttons (compact and aligned right)
        row_right = split.row(align=True)
        row_right.alignment = 'RIGHT'

        # Add new chord button
        op = row_right.operator("chordsong.mapping_add", text="", icon="ADD", emboss=True)
        op.group = group_name
        op.context = prefs.mapping_context_tab
        row_right.separator()

        # Sort group button
        op = row_right.operator("chordsong.mapping_sort_group", text="", icon="SORTALPHA", emboss=True)
        op.group_name = group_name
        row_right.separator()

        # Rename, Move, and Delete group buttons
        if group_name != "Ungrouped":
            group_idx = _get_group_index(prefs, group_name)
            if group_idx is not None:
                # Move up button
                op = row_right.operator("chordsong.group_move_up", text="", icon="TRIA_UP", emboss=False)
                op.index = group_idx
                # Move down button
                op = row_right.operator("chordsong.group_move_down", text="", icon="TRIA_DOWN", emboss=False)
                op.index = group_idx
                row_right.separator()
                # Edit group button (name and icon)
                op = row_right.operator("chordsong.group_edit", text="", icon="GREASEPENCIL", emboss=False)
                op.index = group_idx
                row_right.separator()
                # Delete group button
                op = row_right.operator("chordsong.group_remove", text="", icon="TRASH", emboss=False)
                op.index = group_idx

        if not is_expanded:
            continue

        col.separator()
        # Pass all mappings for conflict checking and search query for auto-expansion
        for idx, m, readonly in items:
            if readonly:
                # Foreign (other-context) chord shown for reference: greyed,
                # not editable here. Tagged with its home so the user knows
                # where to edit it.
                # Clickable, not just a label: from the Global tab there is
                # no other way to reach the editor this chord lives in, and
                # the row itself is read-only.
                foreign = getattr(m, "context", "") or DEFAULT_CONTEXT
                home = context_label(foreign)
                tag = col.row(align=True)
                tag.alignment = 'LEFT'
                tag.prop_enum(prefs, "mapping_context_tab", foreign,
                              text=f"{home} chord — open its tab",
                              icon='WORLD' if foreign == ALL_CONTEXT else 'FILE_ALIAS')
                ro = col.column()
                ro.enabled = False
                draw_mapping_item(prefs, m, idx, ro, all_mappings=prefs.mappings,
                                  search_query=search_query, conflicts=conflicts)
            else:
                draw_mapping_item(prefs, m, idx, col, all_mappings=prefs.mappings,
                                  search_query=search_query, conflicts=conflicts)
            # Extra spacing between item boxes
            col.separator(factor=2.0)

    col.separator()


def _draw_context_rollouts(prefs, context, layout, conflicts=None):
    """Top of the Mappings tab: leader key, modifier, Global and one boxed
    rollout per editor — all rows in one two-column table.

    Design rules (keep them when editing):
      * One row grammar everywhere: [arrow cell][control ...]. The header is
        one full-width editor button; body rows are a two-cell grid (the
        Leader Key line and the mode buttons), so all vertical edges coincide. The arrow
        cell is a fixed width (_ROLLOUT_ARROW_UNITS_X), blank where a row
        has no arrow, so every control starts at the same x. Controls run
        to the box's right edge: header buttons, mode buttons and the
        leader-key line all share both edges. Nothing is content-sized.
      * Counts live inside the button label ("3D View · 114"), not in a
        side column, so buttons can be full width.
      * Two fixed 50/50 columns (a split, not a row of columns) when the
        panel is wide enough, one column otherwise. Column widths never
        depend on content; an open rollout only grows downward. Each
        column starts with a settings box — Leader Key (default) on the
        left, Multi-Toggle Modifier on the right — so those controls line
        up with the editor buttons below them.
      * Open state: prefs.open_editor_families via chordsong.family_toggle;
        selecting a context rolls its family open (prefs update callback);
        the arrow and, for the active editor, the header button collapse it.
        A rollout body holds the editor's mode buttons. The
        editor's own leader key is the first body row: greyed with an
        Override icon while it follows the default, live with a reset arrow
        once overridden.
      * Colour carries meaning only: a collapsed header turns red when any
        of its contexts has a conflict; open, the offending mode button is
        red instead.
    """
    from ...operators.mapping.family_toggle import leader_override_spaces, open_families

    wm = context.window_manager
    keyconfigs = (wm.keyconfigs.user, wm.keyconfigs.addon)
    master_km, master_kmi = find_leader_kmi(MASTER_KEYMAP_NAME, keyconfigs)
    master_event = leader_event(master_kmi)

    current = prefs.mapping_context_tab
    conflicted = contexts_with_conflicts(prefs.mappings, conflicts)
    opened = open_families(prefs)
    # Which editors have their own leader key. The stored set is
    # authoritative, but an editor whose binding already differs — one the
    # user edited in Blender's own keymap editor, say — counts too, so the
    # UI can never claim "follows the default" while it does not.
    overridden = leader_override_spaces(prefs)
    counts = {}
    for m in prefs.mappings:
        tok = getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT
        counts[tok] = counts.get(tok, 0) + 1

    def _with_count(text, n):
        return f"{text}  \u00b7  {n}" if n else text

    def _row(box, *, arrow=None):
        """[arrow cell][...]: returns the control area of one grammar row.
        arrow — None for a blank cell, else (space_type, is_open, enabled)."""
        row = box.row(align=True)
        cell = row.row(align=True)
        cell.ui_units_x = _ROLLOUT_ARROW_UNITS_X
        if arrow is None:
            cell.label(text="", icon='BLANK1')
        else:
            space_type, is_open, enabled = arrow
            cell.enabled = enabled
            op = cell.operator("chordsong.family_toggle", text="",
                               icon='TRIA_DOWN' if is_open else 'TRIA_RIGHT', emboss=False)
            op.space_type = space_type
        return row.row(align=True)

    def _labelled(control_row, text, icon='NONE'):
        """Label in a fixed-width cell, then the remaining width for controls."""
        lab = control_row.row(align=True)
        lab.ui_units_x = _ROLLOUT_LABEL_UNITS_X
        lab.label(text=text, icon=icon)
        return control_row.row(align=True)

    # --- context boxes ---------------------------------------------------
    def _key_cell(cell, key):
        """The editor's own leader key, in the last third of a header row.
        key — None (blank cell), or (km, kmi, space_type, differs, live).
        The key field is always shown; it is greyed while the editor still
        follows the default key, with an Override icon beside it. Once the
        user presses Override (or the key differs) the field is live and the
        icon becomes a reset arrow."""
        if key is None:
            cell.label(text="")
            return
        if key == "master":
            # 3D View: its key is the default set at the top — shown greyed,
            # no override control (there is nothing to override it against).
            if master_kmi is not None and master_km is not None:
                field = cell.row(align=True)
                field.enabled = False
                field.context_pointer_set("keymap", master_km)
                field.prop(master_kmi, "type", text="", full_event=True, emboss=True)
            else:
                cell.label(text="")
            return
        km, kmi, space_type, differs, live = key
        field = cell.row(align=True)
        field.enabled = live
        field.context_pointer_set("keymap", km)
        field.prop(kmi, "type", text="", full_event=True, emboss=True)
        op = cell.operator("chordsong.leader_override_toggle", text="",
                           icon='LOOP_BACK' if live else 'DECORATE_OVERRIDE')
        op.space_type = space_type

    def _thirds(row):
        """Split a body control area into the same cells as a mode row:
        label / first button on the left, key cell on the right."""
        split = row.split(factor=_ROLLOUT_NAME_SHARE, align=True)
        return split.row(align=True), split.row(align=True)

    def _draw_global(parent):
        box = parent.box()
        name = _row(box)
        name.alert = ALL_CONTEXT in conflicted
        # Same pressed-button styling as the editor headers
        op = name.operator("chordsong.context_select",
                           text=_with_count("Global", counts.get(ALL_CONTEXT, 0)),
                           icon='WORLD', depress=(current == ALL_CONTEXT))
        op.token = ALL_CONTEXT

    def _draw_family(parent, space_type, family_label, family_icon):
        members = family_contexts(space_type)
        if not members:
            return
        tokens = [c.token for c in members]
        total = sum(counts.get(t, 0) for t in tokens)
        selected_here = current in tokens
        is_open = space_type in opened
        family_alert = any(t in conflicted for t in tokens)

        # This editor's own leader key (the 3D View *is* the default above)
        key = None
        km_name = _KEYMAP_BY_SPACE.get(space_type)
        if km_name == MASTER_KEYMAP_NAME:
            key = "master"
        elif km_name:
            km, kmi = find_leader_kmi(km_name, keyconfigs)
            if km is not None and kmi is not None:
                differs = (space_type in overridden
                           or (master_event is not None and leader_event(kmi) != master_event))
                key = (km, kmi, space_type, differs, differs)

        box = parent.box()
        # Header: the editor button spans the full control width. An operator
        # button rather than prop_enum so it stays highlighted while any of
        # the editor's modes is selected.
        name = _row(box, arrow=(space_type, is_open, True))
        name.alert = family_alert and not is_open
        if len(members) > 1:
            # The count is the whole family's, so the header must not also
            # select one context — clicking "3D View · 114" and landing on
            # Object's 84 rows made the label a lie. Header rolls; the body
            # buttons, each with its own count, select.
            op = name.operator("chordsong.family_toggle", text=_with_count(family_label, total),
                               icon=family_icon, depress=selected_here)
            op.space_type = space_type
        else:
            # Single-context editor: nothing in the body to select, so the
            # header is the selector and its count is that context's own.
            op = name.operator("chordsong.context_select", text=_with_count(family_label, total),
                               icon=family_icon, depress=selected_here)
            op.token = tokens[0]
        if not is_open:
            return

        # Body row 1: the editor's leader key, in the two-cell grid
        # [label | field + Override/reset icon] the mode rows use too.
        if key is not None:
            label_cell, key_cell = _thirds(_row(box))
            label_cell.enabled = False
            label_cell.label(text="Leader Key", icon='KEYINGSET')
            _key_cell(key_cell, key)

        # Body rows: context buttons, _ROLLOUT_MODES_PER_ROW equal cells per
        # row; a short last row is padded so its buttons keep the width.
        # The family's ungrouped contexts come first, then each group
        # (EditorContext.group, e.g. "Edit Modes") under a greyed caption.
        if len(members) < 2:
            return

        def _mode_rows(items):
            for start in range(0, len(items), _ROLLOUT_MODES_PER_ROW):
                chunk = items[start:start + _ROLLOUT_MODES_PER_ROW]
                buttons = _row(box)
                for ctx in chunk:
                    cell = buttons.row(align=True)
                    cell.alert = ctx.token in conflicted
                    cell.prop_enum(prefs, "mapping_context_tab", ctx.token,
                                   text=_with_count(context_short_label(ctx.token), counts.get(ctx.token, 0)),
                                   icon=ctx.icon)
                for _ in range(_ROLLOUT_MODES_PER_ROW - len(chunk)):
                    buttons.row(align=True).label(text="")

        _mode_rows(list(contexts_in_group(space_type)))
        for caption_text in group_captions(space_type):
            grouped = list(contexts_in_group(space_type, caption_text))
            caption = _row(box)
            caption.enabled = False
            caption.label(text=caption_text, icon='DOT')
            _mode_rows(grouped)

    # --- settings boxes -------------------------------------------------
    def _draw_leader_key_box(parent):
        box = parent.box()
        row = _row(box)
        ctrl = _labelled(row, "Leader Key (default)", icon='KEYINGSET')
        if master_kmi is not None and master_km is not None:
            ctrl.context_pointer_set("keymap", master_km)
            ctrl.prop(master_kmi, "type", text="", full_event=True, emboss=True)
            # A master binding that differs from the last one we recorded means
            # the user just changed it: propagate to the editors still on the
            # old key (explicit per-editor overrides are kept). An empty record
            # is the first draw: record only.
            # Compare the whole binding, so a change to Ctrl+Space
            # propagates like any other. Editors with their own key are
            # skipped rather than overwritten.
            signature = event_signature(master_kmi)
            last = getattr(prefs, "leader_key_last", "") or ""
            if signature != last:
                skip = [_KEYMAP_BY_SPACE[sp] for sp in leader_override_spaces(prefs)
                        if sp in _KEYMAP_BY_SPACE]
                schedule_master_sync(signature, propagate=bool(last), skip_keymaps=skip)
        else:
            ctrl.label(text="Leader keymap not found", icon='ERROR')
        overrides = leader_overrides(keyconfigs)
        if overrides:
            note = _row(box)
            note.enabled = False
            n = len(overrides)
            note.label(text=f"{n} editor{'s use' if n != 1 else ' uses'} its own key (see its rollout)", icon='INFO')

    def _draw_modifier_box(parent):
        box = parent.box()
        row = _row(box)
        ctrl = _labelled(row, "Multi-Toggle Modifier")
        ctrl.prop(prefs, "toggle_multi_modifier", text="")
        # Selecting a context opens its rollout, so they accumulate; without
        # this the table grows until it pushes the mapping list off-screen.
        tail = row.row(align=True)
        tail.alignment = 'RIGHT'
        tail.enabled = bool(opened)
        collapse = tail.operator("chordsong.family_toggle", text="", icon='TRIA_UP_BAR')
        collapse.space_type = _COLLAPSE_ALL

    # --- columns -----------------------------------------------------------
    try:
        # region.width is device pixels but every fixed cell here is in UI
        # units, so divide out the interface scale before comparing.
        scale = getattr(getattr(context.preferences, "view", None), "ui_scale", 1.0) or 1.0
        width = (context.region.width / max(scale, 0.1)) if context and context.region else 0
    except Exception:  # pylint: disable=broad-exception-caught
        width = 0
    families = list(EDITOR_FAMILIES)
    if width >= _ROLLOUT_TWO_COLUMN_MIN_PX:
        # A 50/50 split, not a row of two columns: a row hands width to
        # whichever column has the wider content and would jerk on open.
        outer = layout.split(factor=0.5, align=False)
        left = outer.column(align=False)
        right_wrap = outer.row(align=False)
        right_wrap.separator(factor=_ROLLOUT_COLUMN_GAP)
        right = right_wrap.column(align=False)
        half = (len(families) + 1) // 2
        _draw_leader_key_box(left)
        _draw_modifier_box(right)
        _draw_global(left)
        for fam in families[:half]:
            _draw_family(left, *fam)
        for fam in families[half:]:
            _draw_family(right, *fam)
    else:
        col = layout.column(align=False)
        _draw_leader_key_box(col)
        _draw_modifier_box(col)
        _draw_global(col)
        for fam in families:
            _draw_family(col, *fam)


def _get_group_expansion_state(prefs, group_name):
    """Retrieve expansion state for a group."""
    if group_name == "Ungrouped":
        return prefs.ungrouped_expanded, prefs, "ungrouped_expanded"

    for grp in prefs.groups:
        if grp.name == group_name:
            return grp.expanded, grp, "expanded"

    return True, None, None


def _get_group_index(prefs, group_name):
    """Retrieve group index by name."""
    for idx, grp in enumerate(prefs.groups):
        if grp.name == group_name:
            return idx
    return None
