"""
Mappings tab for addon preferences.

Layout (two fixed columns; one boxed row per editor):
  ┌ Leader Key (default)  [Space Bar]        ┐ ┌ Multi-Toggle Modifier  [Ctrl]     ┐
  └──────────────────────────────────────────┘ └───────────────────────────────────┘
  ┌ 🌐 Global · 18                            ┐ ┌ Movie Clip · 2        🔑[Tab    ]⧉ ┐
  └──────────────────────────────────────────┘ └───────────────────────────────────┘
  ┌ 3D View · 84 [▣84][◐0][✎0][🦴0] 🔑[Space]  ┐ ┌ Dope Sheet · 3 [▤3][◷0]  🔑[Tab]↶ ┐
  └──────────────────────────────────────────┘ └───────────────────────────────────┘
  ┌ Edit Modes · 30 [△30][∿0][🦴0][A0][#0][●0][✏0][⁘0] ┐  …
  └──────────────────────────────────────────┘
  [Add Chord] [Conflicts] [Add Group] …
  [Search…]                                              [Copy] [Paste]
  ▾ Group … mapping rows …
One row per editor family (core.contexts.EDITOR_FAMILIES): the editor
button (selects the editor's base context), its contexts as [icon count]
chips, and the editor's own leader key (🔑 icon, field, ⧉ Override / ↶
reset). A context group (EditorContext.group — the 3D View's Edit Modes,
too many chips for the editor's row) gets a row of its own right under
its editor. The default leader key is a binding of its own (see ui.keymap)
and propagates to every editor that follows it; any editor, the 3D View
included, can override it.
"""

from ...core.contexts import (
    ALL_CONTEXT,
    DEFAULT_CONTEXT,
    EDITOR_FAMILIES,
    GROUP_ICONS,
    LEADER_KEYMAPS,
    context_chain,
    context_label,
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

# The context selector flows into two columns when the preferences region
# is at least this wide (UI pixels); one column below. An editor row needs
# about 33 units — editor name, four [icon count] chips, key cell — so two
# columns plus the sidebar want ~1500.
_SELECTOR_TWO_COLUMN_MIN_PX = 1500
# Fixed label cell for the "Leader Key (default)" / "Multi-Toggle Modifier"
# lines so their fields line up.
_SELECTOR_LABEL_UNITS_X = 9.0
_SELECTOR_COLUMN_GAP = 1.0
# Editor row shares: editor button, then [icon count] chips, then the
# editor's own leader key cell ([key icon][field][Override/reset]). A
# group row keeps the grammar with a blank key cell.
_ROW_NAME_SHARE = 0.37
_ROW_KEY_SHARE = 0.23
# Gap between a row's button and its first chip (UILayout.separator factor).
_CHIP_GAP = 1.5
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

    _draw_context_selector(prefs, context, root, conflicts)
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
            if search_query:
                # A search spans every context: "where is my Cavity chord"
                # must be answerable from any tab. Foreign hits are listed
                # read-only with a link to their own tab.
                pass
            elif mapping_context in inherited_counts:
                # Counted after the search filter below, so the link never
                # advertises more rows than the list shows.
                if not conflicts_with_any(conflicts, idx, own_indices):
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


def _draw_context_selector(prefs, context, layout, conflicts=None):
    """Top of the Mappings tab: leader key, modifier, Global and one boxed
    row per editor (plus one per context group) in a two-column table.

    Design rules (keep them when editing):
      * One row grammar: three fixed shares (_ROW_NAME_SHARE, the rest,
        _ROW_KEY_SHARE). An editor row is the editor button; that editor's
        contexts as [icon count] chips in a fixed number of even cells (the
        widest family's count, padded on the left); the editor's own
        leader key as [key icon][field][Override/reset]. So buttons end,
        chips align and key fields start at the same x in every row. A
        single-context editor has no chips and its button takes their
        share too. A group row (EditorContext.group, e.g. Edit Modes) has
        the same grammar; its chips wrap `chip_slots` per line, its button
        spans the lines, and its key cell is blank — it has no key of its
        own yet, it uses its editor's. A small gap sits between every
        button and its first chip. Controls run to the box's right edge.
        Nothing is content-sized.
      * Counts live inside the button label ("3D View · 84", a chip's
        bare "84" — "0" when empty, so the chip keeps its width), not in a
        side column, so controls can be full width. A row's count is the
        sum of its own chips, so an editor and its group never double
        count. A chip's icon is its only name; the full label is its
        tooltip.
      * Two fixed 50/50 columns (a split, not a row of columns) when the
        panel is wide enough, one column otherwise. Column widths never
        depend on content. Each column starts with a settings box — Leader
        Key (default) on the left, Multi-Toggle Modifier on the right — so
        those controls line up with the editor buttons below them.
      * A row's button selects its first context (the editor's base mode,
        the group's first mode), so clicking a row always lights it up.
        Nothing rolls open or closed; every context is one click away.
      * The key field is greyed with an Override icon while the editor
        follows the default key, live with a reset arrow once overridden.
      * Colour carries meaning only: a row's button turns red when any of
        its chips has a conflict, and the offending chip is red too.
    """
    from ...operators.mapping.context_select import leader_override_spaces

    wm = context.window_manager
    keyconfigs = (wm.keyconfigs.user, wm.keyconfigs.addon)
    master_km, master_kmi = find_leader_kmi(MASTER_KEYMAP_NAME, keyconfigs)
    master_event = leader_event(master_kmi)

    current = prefs.mapping_context_tab
    conflicted = contexts_with_conflicts(prefs.mappings, conflicts)
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

    # Chip cells per editor row: the widest family's ungrouped count, so
    # every row splits the same way and chips align across editors.
    chip_slots = max((len(contexts_in_group(space)) for space, _, _ in EDITOR_FAMILIES
                      if len(family_contexts(space)) > 1), default=1)

    def _row(box):
        """The control area of one boxed row."""
        return box.row(align=True)

    def _labelled(control_row, text, icon='NONE'):
        """Label in a fixed-width cell, then the remaining width for controls."""
        lab = control_row.row(align=True)
        lab.ui_units_x = _SELECTOR_LABEL_UNITS_X
        lab.label(text=text, icon=icon)
        return control_row.row(align=True)

    def _chip(cell, ctx):
        """One context as [icon count]: the icon is its identity, the
        count its weight; the full name is the tooltip (the operator's
        description is built from the token)."""
        clashing = ctx.token in conflicted
        cell.alert = clashing
        # An operator button, not prop_enum: Blender's radio buttons do
        # not take the alert tint, so a conflicted context stayed grey.
        # The icon is kept even when clashing — swapping it for ERROR
        # would strip the chip of the only thing that names it.
        # A zero count is drawn as "0", never as no text: an icon-only
        # button is laid out as fixed-size and centres its icon, so an
        # empty chip shrank to the icon and left a hole in the row.
        op = cell.operator("chordsong.context_select", text=str(counts.get(ctx.token, 0)),
                           icon=ctx.icon, depress=(current == ctx.token))
        op.token = ctx.token

    def _chip_grid(parent_row, slots):
        """`slots` equal cells for chips. A grid_flow, not a row: a row
        hands its spare width to items in proportion to their text, so
        "87" came out wider than "0"; even_columns makes every cell the
        same width whatever it holds."""
        return parent_row.grid_flow(row_major=True, columns=slots,
                                    even_columns=True, even_rows=False, align=True)

    def _row_button(cell, text, icon, members):
        """The button that opens a row: selects the row's first context,
        lit while any of the row's contexts is selected, red while any has
        a conflict. An operator button rather than prop_enum so it stays
        highlighted while any of the row's modes is selected."""
        tokens = [c.token for c in members]
        cell.alert = any(t in conflicted for t in tokens)
        total = sum(counts.get(t, 0) for t in tokens)
        op = cell.operator("chordsong.context_select", text=_with_count(text, total),
                           icon=icon, depress=(current in tokens))
        op.token = tokens[0]

    # --- context boxes ---------------------------------------------------
    def _key_cell(cell, key):
        """The editor's own leader key, the last cell of its row:
        [key icon][field][Override/reset]. The icon is the only caption —
        the row has no room for the words. key — None (blank cell) or
        (km, kmi, space_type, differs, live). The field is greyed while the
        editor still follows the default key, with an Override icon beside
        it; once the user presses Override (or the key differs) the field
        is live and the icon becomes a reset arrow."""
        if key is None:
            cell.label(text="")
            return
        cell.label(text="", icon='KEYINGSET')
        km, kmi, space_type, differs, live = key
        field = cell.row(align=True)
        field.enabled = live
        field.context_pointer_set("keymap", km)
        field.prop(kmi, "type", text="", full_event=True, emboss=True)
        op = cell.operator("chordsong.leader_override_toggle", text="",
                           icon='LOOP_BACK' if live else 'DECORATE_OVERRIDE')
        op.space_type = space_type

    def _draw_global(parent):
        box = parent.box()
        name = _row(box)
        name.alert = ALL_CONTEXT in conflicted
        # Same pressed-button styling as the editor rows
        op = name.operator("chordsong.context_select",
                           text=_with_count("Global", counts.get(ALL_CONTEXT, 0)),
                           icon='WORLD', depress=(current == ALL_CONTEXT))
        op.token = ALL_CONTEXT

    def _draw_family(parent, space_type, family_label, family_icon):
        members = family_contexts(space_type)
        if not members:
            return

        # This editor's own leader key, following the default until overridden
        key = None
        km_name = _KEYMAP_BY_SPACE.get(space_type)
        if km_name:
            km, kmi = find_leader_kmi(km_name, keyconfigs)
            if km is not None and kmi is not None:
                differs = (space_type in overridden
                           or (master_event is not None and leader_event(kmi) != master_event))
                key = (km, kmi, space_type, differs, differs)

        # Editor row: [editor button | chip slots | key cell], fixed shares
        # (_ROW_NAME_SHARE / _ROW_KEY_SHARE), so every editor ends its
        # button, lines up its chips and starts its key field at the same
        # x. The chip slots are `chip_slots` even cells (the widest
        # family's count), padded on the left; a single-context editor has
        # no chips and its button takes their share too.
        # A single-context editor has no chips: its button selects that one
        # context and the chip slots stay blank, so the row still reads
        # like every other.
        chips = list(contexts_in_group(space_type)) if len(members) > 1 else []
        # The button counts and lights up for its own chips only; the
        # group rows below carry theirs.
        _context_row(parent, family_label, family_icon, chips or members, chips, key)

        # Group rows (EditorContext.group): one box each, right under the
        # editor, in the same grammar, so the group's chips sit in the
        # editor's chip columns. A group has no key of its own (yet): its
        # key cell is blank.
        for caption in group_captions(space_type):
            grouped = list(contexts_in_group(space_type, caption))
            _context_row(parent, caption, GROUP_ICONS.get(caption, 'DOT'), grouped, grouped, None)

    def _context_row(parent, text, icon, members, chips, key):
        """One boxed row [button | chip slots | key cell] in the fixed
        shares. The button selects the first of `members` and lights up
        for any of them; `chips` are laid out `chip_slots` per line (padded
        on the left, blank when there are none). More chips than slots
        wrap onto further lines and the button grows to span them; the key
        cell stays on the first line."""
        lines = max(1, -(-len(chips) // chip_slots))
        row = _row(parent.box())
        outer = row.split(factor=1.0 - _ROW_KEY_SHARE, align=True)
        lead = outer.row(align=True)
        key_col = outer.column(align=True)
        split = lead.split(factor=_ROW_NAME_SHARE / (1.0 - _ROW_KEY_SHARE), align=True)
        button = split.row(align=True)
        # Aligned lines in a column stack with no gap, so a button scaled
        # by the line count spans them exactly.
        button.scale_y = lines
        _row_button(button, text, icon, members)
        chip_col = split.column(align=True)
        for start in range(0, max(len(chips), 1), chip_slots):
            chunk = chips[start:start + chip_slots]
            line = chip_col.row(align=True)
            # A breath between the button and its chips.
            line.separator(factor=_CHIP_GAP)
            grid = _chip_grid(line, chip_slots)
            for _ in range(chip_slots - len(chunk)):
                grid.label(text="")
            for ctx in chunk:
                _chip(grid.row(align=True), ctx)
        _key_cell(key_col.row(align=True), key)
        for _ in range(lines - 1):
            key_col.row(align=True).label(text="")

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
            # Same row as the field, at its right end: the box stays one
            # line tall and level with the Multi-Toggle Modifier box.
            note = row.row(align=True)
            note.alignment = 'RIGHT'
            note.enabled = False
            n = len(overrides)
            note.label(text=f"{n} editor{'s use' if n != 1 else ' uses'} its own key", icon='INFO')

    def _draw_modifier_box(parent):
        box = parent.box()
        row = _row(box)
        ctrl = _labelled(row, "Multi-Toggle Modifier")
        ctrl.prop(prefs, "toggle_multi_modifier", text="")

    # --- columns -----------------------------------------------------------
    try:
        # region.width is device pixels but every fixed cell here is in UI
        # units, so divide out the interface scale before comparing.
        scale = getattr(getattr(context.preferences, "view", None), "ui_scale", 1.0) or 1.0
        width = (context.region.width / max(scale, 0.1)) if context and context.region else 0
    except Exception:  # pylint: disable=broad-exception-caught
        width = 0
    families = list(EDITOR_FAMILIES)
    if width >= _SELECTOR_TWO_COLUMN_MIN_PX:
        # A 50/50 split, not a row of two columns: a row hands width to
        # whichever column has the wider content and would jerk on redraw.
        outer = layout.split(factor=0.5, align=False)
        left = outer.column(align=False)
        right_wrap = outer.row(align=False)
        right_wrap.separator(factor=_SELECTOR_COLUMN_GAP)
        right = right_wrap.column(align=False)
        # Balance the columns by row lines, not by family count: Global and
        # the group rows (Edit Modes, two lines) all land on the left, so
        # the left column fills up after fewer editors.
        def _lines(space):
            return 1 + sum(-(-len(contexts_in_group(space, g)) // chip_slots)
                           for g in group_captions(space))
        total = 1 + sum(_lines(space) for space, _, _ in families)
        _draw_leader_key_box(left)
        _draw_modifier_box(right)
        _draw_global(left)
        used = 1
        column = left
        for fam in families:
            if column is left and used >= total / 2:
                column = right
            _draw_family(column, *fam)
            used += _lines(fam[0])
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
