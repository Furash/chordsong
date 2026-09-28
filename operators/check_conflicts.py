"""Operator to check for chord mapping conflicts."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error
# pylint: disable=unsubscriptable-object

import string

import bpy  # type: ignore

from .common import prefs, schedule_autosave_safe
from ..core.engine import split_chord, get_str_attr

def _check_chord_conflicts(new_key: tuple, chords_to_check: list) -> bool:
    """Check if new_key conflicts with any chord in the list.

    Returns True if conflict exists (exact match, prefix, or blocked).
    """
    for existing in chords_to_check:
        existing_key = tuple(split_chord(existing))

        # Exact match
        if new_key == existing_key:
            return True

        # New chord is prefix of existing
        if len(new_key) < len(existing_key) and existing_key[:len(new_key)] == new_key:
            return True

        # Existing is prefix of new chord
        if len(existing_key) < len(new_key) and new_key[:len(existing_key)] == existing_key:
            return True

    return False

def _schedule_recheck():
    """Schedule a re-run of the conflict checker."""
    # pylint: disable=protected-access
    if CHORDSONG_OT_CheckConflicts._recheck_pending:
        return

    CHORDSONG_OT_CheckConflicts._recheck_pending = True
    prefs_ctx = CHORDSONG_OT_CheckConflicts._prefs_context

    def recheck():
        CHORDSONG_OT_CheckConflicts._recheck_pending = False
        if prefs_ctx and isinstance(prefs_ctx, dict):
            try:
                # Type: ignore is needed because Pylint doesn't understand dict unpacking
                with bpy.context.temp_override(**prefs_ctx):  # pylint: disable=not-a-mapping
                    bpy.ops.chordsong.check_conflicts('INVOKE_DEFAULT')
            except (TypeError, RuntimeError):
                # Context is invalid (e.g., preferences window closed), use default
                bpy.ops.chordsong.check_conflicts('INVOKE_DEFAULT')
        else:
            bpy.ops.chordsong.check_conflicts('INVOKE_DEFAULT')
        return None

    bpy.app.timers.register(recheck, first_interval=1.5)

def generate_chord(base_chord, all_chords, exclude_chord=None, exclude_symbols=None, change_last=False):
    """Shared utility function to generate a non-conflicting chord.

    Args:
        base_chord: The base chord to modify
        all_chords: List of existing chord strings to check against
        exclude_chord: Optional chord string to explicitly exclude
        exclude_symbols: List of symbols to skip (for unique suggestions)
        change_last: If True, change last symbol; if False, add new symbol
    """
    base_tokens = split_chord(base_chord)
    if not base_tokens:
        print(f"Warning: generate_chord got empty tokens for '{base_chord}'")
        return None

    exclude_symbols = exclude_symbols or []
    base_key = tuple(base_tokens)
    if change_last:
        chords_to_check = all_chords
    else:
        chords_to_check = [c for c in all_chords if tuple(split_chord(c)) != base_key]

    # Try all letters (lowercase then uppercase)
    all_letters = string.ascii_lowercase + string.ascii_uppercase

    for letter in all_letters:
        if letter in exclude_symbols:
            continue

        if change_last:
            if base_tokens[-1] == letter:
                continue
            new_tokens = base_tokens[:-1] + [letter]
        else:
            new_tokens = base_tokens + [letter]

        new_chord = " ".join(new_tokens)
        new_key = tuple(new_tokens)

        if exclude_chord and new_chord == exclude_chord:
            continue

        if not _check_chord_conflicts(new_key, chords_to_check):
            return new_chord

    # Try numbers if adding
    if not change_last:
        for num in "1234567890":
            if num in exclude_symbols:
                continue
            new_tokens = base_tokens + [num]
            new_key = tuple(new_tokens)
            if not _check_chord_conflicts(new_key, chords_to_check):
                return " ".join(new_tokens)

    # Fallback: find any valid non-conflicting chord
    fallback_alphabet = "abcdefghijklmnopqrstuvwxyz1234567890"
    if change_last:
        indices = range(len(base_tokens) - 1, -1, -1)
    else:
        indices = range(len(base_tokens))

    for i in indices:
        for sym in fallback_alphabet:
            if sym in exclude_symbols:
                continue

            new_tokens = list(base_tokens)
            if i < len(new_tokens):
                if new_tokens[i] == sym:
                    continue
                new_tokens[i] = sym

            # Check for exact matches and prefixes
            new_key = tuple(new_tokens)
            if not _check_chord_conflicts(new_key, chords_to_check):
                return " ".join(new_tokens)

    # Absolute last resort - just return something that is likely unique
    # We use a timestamp-like suffix or just keep trying more symbols
    suffix_list = "xyzuvwabcdefghijklmnopqrst0123456789"
    for s in suffix_list:
        if s not in exclude_symbols:
            if change_last and len(base_tokens) > 0:
                return " ".join(base_tokens[:-1] + [s])
            else:
                return " ".join(base_tokens + [s])

    # If all else fails
    return base_chord + " x"

def find_conflicts_util(mappings, generate_fixes=True):
    """Shared utility function to find all chord conflicts.

    Conflicts are evaluated per *effective* context: for every editor
    context, the chords active there are its own, those inherited from
    parent contexts (3D View chords in Sculpt mode, Sequencer chords in the
    Preview, ...) and Global ones. A conflict found in several effective
    contexts (e.g. two Global duplicates) is reported once.

    Args:
        mappings: Collection of mapping objects to check
        generate_fixes: If True, generate suggested fixes (expensive). If False, only detect conflicts.

    Returns a dict with 'prefix_conflicts' and 'duplicates' lists.
    """
    from ..core.contexts import (
        ALL_CONTEXT, CONTEXT_TOKENS, DEFAULT_CONTEXT, context_active_in, context_label,
    )

    conflicts = {"prefix_conflicts": [], "duplicates": []}
    enabled = [m for m in mappings if getattr(m, "enabled", True)]
    seen_duplicates = set()
    seen_prefixes = set()

    def _ctx_of(m):
        return getattr(m, "context", DEFAULT_CONTEXT) or DEFAULT_CONTEXT

    def _context_label(involved, live_ctx):
        # "ALL", "VIEW_3D", or "ALL/VIEW_3D_SCULPT" when several contexts meet
        ctxs = []
        for m in involved:
            c = _ctx_of(m)
            if c not in ctxs:
                ctxs.append(c)
        # Human-readable, like every other context label in the UI
        if len(ctxs) == 1:
            return context_label(ctxs[0])
        ordered = sorted(ctxs, key=lambda c: (c != ALL_CONTEXT, c != live_ctx, c))
        return " / ".join(context_label(c) for c in ordered)

    for live_ctx in CONTEXT_TOKENS:
        ctx_mappings = [m for m in enabled if context_active_in(_ctx_of(m), live_ctx)]
        if not ctx_mappings:
            continue

        chord_map = {}
        all_chords = []
        for m in ctx_mappings:
            chord_str = get_str_attr(m, "chord")
            tokens = split_chord(chord_str)
            if not tokens:
                continue
            all_chords.append(chord_str)
            chord_map.setdefault(tuple(tokens), []).append(m)

        # Duplicates: same chord bound more than once in this effective context
        for chord_key, mappings_list in chord_map.items():
            if len(mappings_list) < 2:
                continue
            dedupe_key = frozenset(id(m) for m in mappings_list)
            if dedupe_key in seen_duplicates:
                continue
            seen_duplicates.add(dedupe_key)

            base_chord = " ".join(chord_key)
            conflict_data = {
                "chord": base_chord,
                "context": _context_label(mappings_list, live_ctx),
                "count": len(mappings_list),
                "labels": [get_str_attr(m, "label") for m in mappings_list],
                "groups": [get_str_attr(m, "group") for m in mappings_list],
                "mappings": mappings_list,
            }

            if generate_fixes:
                fixes = {"add": [], "change_last": []}
                for strategy in fixes:
                    # Never test candidate fixes against the duplicates
                    # themselves — the existing chord would block them all.
                    temp_chords = [c for c in all_chords if tuple(split_chord(c)) != chord_key]
                    used_symbols = []
                    for _ in mappings_list:
                        fix = generate_chord(
                            base_chord, temp_chords,
                            exclude_symbols=used_symbols,
                            change_last=(strategy == "change_last")
                        )
                        if fix:
                            fixes[strategy].append(fix)
                            temp_chords.append(fix)
                            fix_tokens = split_chord(fix)
                            if strategy == "change_last":
                                used_symbols.append(fix_tokens[-1])
                            elif len(fix_tokens) > len(chord_key):
                                used_symbols.append(fix_tokens[-1])
                conflict_data["suggested_fixes_add"] = fixes["add"]
                conflict_data["suggested_fixes_change_last"] = fixes["change_last"]

            conflicts["duplicates"].append(conflict_data)

        # Prefix conflicts: one chord is a prefix of another (shorter one wins, longer never fires)
        chord_keys = list(chord_map.keys())
        for i, chord1 in enumerate(chord_keys):
            for chord2 in chord_keys[i + 1:]:
                if len(chord1) < len(chord2) and chord2[:len(chord1)] == chord1:
                    prefix_key, full_key = chord1, chord2
                elif len(chord2) < len(chord1) and chord1[:len(chord2)] == chord2:
                    prefix_key, full_key = chord2, chord1
                else:
                    continue

                prefix_mapping = chord_map[prefix_key][0]
                full_mapping = chord_map[full_key][0]
                dedupe_key = (id(prefix_mapping), id(full_mapping))
                if dedupe_key in seen_prefixes:
                    continue
                seen_prefixes.add(dedupe_key)

                prefix_chord = " ".join(prefix_key)
                full_chord = " ".join(full_key)
                conflict_data = {
                    "prefix_chord": prefix_chord,
                    "prefix_label": get_str_attr(prefix_mapping, "label"),
                    "prefix_group": get_str_attr(prefix_mapping, "group"),
                    "full_chord": full_chord,
                    "full_label": get_str_attr(full_mapping, "label"),
                    "full_group": get_str_attr(full_mapping, "group"),
                    "context": _context_label([prefix_mapping, full_mapping], live_ctx),
                    "prefix_mapping": prefix_mapping,
                }
                if generate_fixes:
                    conflict_data["suggested_fix"] = generate_chord(prefix_chord, all_chords, exclude_chord=full_chord)
                conflicts["prefix_conflicts"].append(conflict_data)

    return conflicts

def _are_mappings_identical(m1, m2):
    """Same chord and same action — the identity the Contexts dialog uses.

    Label, icon, group, enabled flag and context are *not* compared. The
    common way to end up with two identical chords is Duplicate, which
    appends "(Copy)" to the label; requiring equal labels meant Merge was
    never offered for exactly the case it exists for.
    """
    from ..core.chord_serialization import mapping_signature
    return mapping_signature(m1) == mapping_signature(m2)


def _has_identical_mappings(mappings_list):
    """Check if there are any identical mappings in the list."""
    for i, m1 in enumerate(mappings_list):
        for m2 in mappings_list[i+1:]:
            if _are_mappings_identical(m1, m2):
                return True
    return False

class CHORDSONG_OT_ApplyConflictFix(bpy.types.Operator):
    """Apply suggested fix for chord conflict"""

    bl_idname = "chordsong.apply_conflict_fix"
    bl_label = "Apply Fix"
    bl_options = {"REGISTER", "UNDO"}

    conflict_index: bpy.props.IntProperty(default=-1)
    conflict_type: bpy.props.StringProperty(default="PREFIX")
    duplicate_strategy: bpy.props.StringProperty(default="ADD")

    def execute(self, context: bpy.types.Context):
        """Apply the fix."""
        # pylint: disable=protected-access
        conflicts_raw = CHORDSONG_OT_CheckConflicts.conflicts
        if not conflicts_raw or not isinstance(conflicts_raw, dict):
            self.report({"WARNING"}, "No conflicts data available")
            return {"CANCELLED"}

        # Type narrowing: conflicts is guaranteed to be a dict at this point
        conflicts: dict = conflicts_raw  # type: ignore[assignment]

        p = prefs(context)
        fixed_label = None

        if self.conflict_type == "PREFIX":
            if self.conflict_index < len(conflicts["prefix_conflicts"]):
                conflict = conflicts["prefix_conflicts"][self.conflict_index]
                if "prefix_mapping" in conflict and "suggested_fix" in conflict:
                    conflict["prefix_mapping"].chord = conflict["suggested_fix"]
                    fixed_label = conflict['prefix_label']

        elif self.conflict_type == "DUPLICATE":
            if self.conflict_index < len(conflicts["duplicates"]):
                dup = conflicts["duplicates"][self.conflict_index]
                fixes_key = f"suggested_fixes_{self.duplicate_strategy.lower()}"

                if fixes_key in dup and dup[fixes_key]:
                    fixed = 0
                    for i, mapping in enumerate(dup["mappings"]):
                        if i < len(dup[fixes_key]):
                            mapping.chord = dup[fixes_key][i]
                            fixed += 1
                    if fixed > 0:
                        fixed_label = f"{fixed} duplicate(s)"

        if not fixed_label:
            self.report({"INFO"}, "Conflict already resolved")
            return {"FINISHED"}

        schedule_autosave_safe(p, delay_s=5.0)
        self.report({"INFO"}, f"Fixed: {fixed_label}")

        # Refresh conflicts - must update the class variable so the dialog sees changes
        # We use a small timer to ensure Blender has processed the property changes
        def delayed_refresh():
            # Get fresh prefs reference
            p_fresh = prefs(bpy.context)
            new_conflicts = find_conflicts_util(p_fresh.mappings, generate_fixes=True)

            # Update the class variable reference directly
            CHORDSONG_OT_CheckConflicts.conflicts = new_conflicts

            # Also update the in-place lists if someone is holding a reference to the old dict
            if conflicts and isinstance(conflicts, dict):
                conflicts["prefix_conflicts"][:] = new_conflicts["prefix_conflicts"]
                conflicts["duplicates"][:] = new_conflicts["duplicates"]

            # Redraw
            region_popup = CHORDSONG_OT_CheckConflicts._popup_region
            if region_popup:
                try:
                    region_popup.tag_redraw()
                    region_popup.tag_refresh_ui()
                except (ReferenceError, TypeError, RuntimeError):
                    pass

            # Redraw all windows - wrap in try-except to handle destroyed areas
            try:
                for window in bpy.context.window_manager.windows:
                    try:
                        screen = window.screen
                        if not screen:
                            continue
                        for area in screen.areas:
                            try:
                                area.tag_redraw()
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass
            return None

        bpy.app.timers.register(delayed_refresh, first_interval=0.1)
        return {"FINISHED"}

class CHORDSONG_OT_MergeIdentical(bpy.types.Operator):
    """Merge duplicate mappings that run the same action for the same chord, keeping the one active in the most editors"""

    bl_idname = "chordsong.merge_identical"
    bl_label = "Merge Identical"
    bl_options = {"REGISTER", "UNDO"}

    conflict_index: bpy.props.IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        """Merge identical mappings."""
        # pylint: disable=protected-access,unsubscriptable-object
        conflicts_raw = CHORDSONG_OT_CheckConflicts.conflicts
        if not conflicts_raw or not isinstance(conflicts_raw, dict):
            self.report({"WARNING"}, "No conflicts data available")
            return {"CANCELLED"}

        # Type narrowing: conflicts is guaranteed to be a dict at this point
        conflicts: dict = conflicts_raw  # type: ignore[assignment]

        if self.conflict_index < 0 or self.conflict_index >= len(conflicts["duplicates"]):
            self.report({"WARNING"}, "Invalid conflict index")
            return {"CANCELLED"}

        dup = conflicts["duplicates"][self.conflict_index]
        mappings_list = dup["mappings"]

        if len(mappings_list) < 2:
            self.report({"INFO"}, "No duplicates to merge")
            return {"FINISHED"}

        p = prefs(context)

        from ..core.contexts import ALL_CONTEXT, context_chain

        def _reach(m):
            # Sort key: Global first, then a parent editor before its
            # sub-views. Merging must keep the copy that fires in the most
            # places, or it silently narrows the chord.
            ctx = getattr(m, "context", "") or ""
            return (ctx != ALL_CONTEXT, len(context_chain(ctx)) if ctx != ALL_CONTEXT else 0)

        # Group identical mappings; keep the widest-reaching one of each group
        to_remove = []
        seen = set()
        for i, m1 in enumerate(mappings_list):
            if i in seen:
                continue
            group = [i] + [j for j in range(i + 1, len(mappings_list))
                           if j not in seen and _are_mappings_identical(m1, mappings_list[j])]
            seen.update(group)
            if len(group) > 1:
                group.sort(key=lambda k: _reach(mappings_list[k]))
                to_remove.extend(mappings_list[k] for k in group[1:])

        if not to_remove:
            self.report({"INFO"}, "No identical mappings found to merge")
            return {"FINISHED"}

        # bpy returns a fresh Python wrapper on every collection access, so
        # `is` never matches; the RNA pointer identifies the row.
        pointers = {m.as_pointer() for m in to_remove}
        prefs_indices_to_remove = [i for i, m in enumerate(p.mappings) if m.as_pointer() in pointers]

        if not prefs_indices_to_remove:
            self.report({"WARNING"}, "Could not find mappings to remove in preferences")
            return {"CANCELLED"}

        # Remove duplicates (in reverse order to maintain indices)
        prefs_indices_to_remove.sort(reverse=True)
        removed_count = 0
        for pref_idx in prefs_indices_to_remove:
            try:
                if pref_idx < len(p.mappings):
                    p.mappings.remove(pref_idx)
                    removed_count += 1
            except (IndexError, RuntimeError, AttributeError) as e:
                # Mapping might have been removed already or index invalid
                print(f"Warning: Could not remove mapping at index {pref_idx}: {e}")
                continue

        if removed_count == 0:
            self.report({"WARNING"}, "No mappings were removed")
            return {"CANCELLED"}

        schedule_autosave_safe(p, delay_s=5.0)
        self.report({"INFO"}, f"Merged {removed_count} identical mapping(s)")

        # Refresh conflicts
        def delayed_refresh():
            p_fresh = prefs(bpy.context)
            new_conflicts = find_conflicts_util(p_fresh.mappings, generate_fixes=True)

            CHORDSONG_OT_CheckConflicts.conflicts = new_conflicts

            if conflicts and isinstance(conflicts, dict):
                conflicts["prefix_conflicts"][:] = new_conflicts["prefix_conflicts"]
                conflicts["duplicates"][:] = new_conflicts["duplicates"]

            # Force redraw of popup region
            region_popup = CHORDSONG_OT_CheckConflicts._popup_region
            if region_popup:
                try:
                    region_popup.tag_redraw()
                    region_popup.tag_refresh_ui()
                except (ReferenceError, TypeError, RuntimeError):
                    pass

            # Force redraw of all areas - wrap in try-except to handle destroyed areas
            try:
                for window in bpy.context.window_manager.windows:
                    try:
                        screen = window.screen
                        if not screen:
                            continue
                        for area in screen.areas:
                            try:
                                area.tag_redraw()
                            except Exception:
                                pass
                        # Also try to redraw the window
                        try:
                            window.tag_redraw()
                        except Exception:
                            pass
                    except Exception:
                        pass
            except Exception:
                pass

            # Force update of window manager
            try:
                bpy.context.window_manager.tag_redraw()
            except (ReferenceError, TypeError, RuntimeError):
                pass

            return None

        bpy.app.timers.register(delayed_refresh, first_interval=0.2)
        return {"FINISHED"}

class CHORDSONG_OT_CheckConflicts(bpy.types.Operator):
    """Check for chord mapping conflicts (prefixes and duplicates)"""

    bl_idname = "chordsong.check_conflicts"
    bl_label = "Check Chord Conflicts"
    bl_options = {"REGISTER"}

    conflicts = None  # Shared conflict state cache
    _recheck_pending = False
    _prefs_context = None
    _popup_region = None

    def invoke(self, context: bpy.types.Context, event):  # pylint: disable=unused-argument
        """Show dialog with conflicts."""
        p = prefs(context)

        self.conflicts = self._find_conflicts(p.mappings)
        CHORDSONG_OT_CheckConflicts.conflicts = self.conflicts

        # Store preferences context for re-running
        prefs_context = {}
        if hasattr(context, "area") and context.area and context.area.type == "PREFERENCES":
            for key in ("area", "region", "space_data"):
                val = getattr(context, key, None)
                if val:
                    prefs_context[key] = val
        CHORDSONG_OT_CheckConflicts._prefs_context = prefs_context or None

        if not self.conflicts["prefix_conflicts"] and not self.conflicts["duplicates"]:
            self.report({"INFO"}, "No chord conflicts found! ✓")
            CHORDSONG_OT_CheckConflicts.conflicts = None
            return {"FINISHED"}

        self._print_to_console()
        return context.window_manager.invoke_props_dialog(self, width=600)

    def execute(self, context: bpy.types.Context):  # pylint: disable=unused-argument
        """Close dialog."""
        return {"FINISHED"}

    def draw(self, context: bpy.types.Context):  # pylint: disable=unused-argument
        """Draw the conflict report in a dialog."""
        layout = self.layout

        # Capture popup region for later refresh (Blender 4.2+)
        region_popup = getattr(context, "region_popup", None)
        if region_popup:
            CHORDSONG_OT_CheckConflicts._popup_region = region_popup

        # Always use class variable to ensure we see latest data
        conflicts_raw = CHORDSONG_OT_CheckConflicts.conflicts
        if not conflicts_raw or not isinstance(conflicts_raw, dict):
            return

        # Type narrowing: conflicts is guaranteed to be a dict at this point
        conflicts: dict = conflicts_raw  # type: ignore[assignment]

        total = len(conflicts["prefix_conflicts"]) + len(conflicts["duplicates"])

        # Compact header - show success when all resolved
        row = layout.row()
        if total == 0:
            row.label(text="✓ All Conflicts Resolved!", icon="CHECKMARK")
        else:
            row.alert = True
            row.label(text=f"⚠ {total} Conflict(s) Found", icon="ERROR")

        # Prefix conflicts - compact layout
        if conflicts["prefix_conflicts"]:
            box = layout.box()
            box.label(text=f"Prefix Conflicts ({len(conflicts['prefix_conflicts'])})")

            for idx, conflict in enumerate(conflicts["prefix_conflicts"]):
                # Build group info string
                prefix_grp = conflict.get('prefix_group') or 'Ungrouped'
                full_grp = conflict.get('full_group') or 'Ungrouped'
                groups_str = f"[{prefix_grp}] vs [{full_grp}]" if prefix_grp != full_grp else f"[{prefix_grp}]"

                row = box.row(align=True)
                # Chord info with groups: "a" blocks "a b" [Group] (VIEW_3D)
                row.label(
                    text=f"'{conflict['prefix_chord']}' blocks '{conflict['full_chord']}' {groups_str} ({conflict['context']})",
                    icon="FORWARD"
                )
                # Fix button with suggested chord (only show if suggested_fix exists)
                if "suggested_fix" in conflict and conflict["suggested_fix"]:
                    op = row.operator(
                        "chordsong.apply_conflict_fix",
                        text=f"→ {conflict['suggested_fix']}",
                        icon="CHECKMARK"
                    )
                    op.conflict_index = idx
                    op.conflict_type = "PREFIX"
                else:
                    # Show button without suggested fix if fix generation failed or wasn't requested
                    row.label(text="(Fix generation unavailable)", icon="INFO")

        # Duplicate chords - table layout

        if conflicts["duplicates"]:
            box = layout.box()
            box.label(text=f"Duplicate Chords ({len(conflicts['duplicates'])})")

            for idx, dup in enumerate(conflicts["duplicates"]):
                dup_box = box.box()

                # Header row with chord and context
                header = dup_box.row(align=True)
                header.label(text=f"'{dup['chord']}' ({dup['context']})", icon="COPYDOWN")

                # Table header row
                table_header = dup_box.row(align=True)
                split = table_header.split(factor=0.5)
                split.label(text="Mapping")
                cols = split.split(factor=0.5)
                cols.label(text="Add Symbol")
                cols.label(text="Change Last")

                # Get fixes
                fixes_add = dup.get("suggested_fixes_add", [])
                fixes_change = dup.get("suggested_fixes_change_last", [])

                # Table rows - one per duplicate entry
                for i, label in enumerate(dup['labels']):
                    grp = dup['groups'][i] if i < len(dup['groups']) else ''
                    grp_str = grp or 'Ungrouped'
                    fix_add = fixes_add[i] if i < len(fixes_add) else "-"
                    fix_change = fixes_change[i] if i < len(fixes_change) else "-"

                    row = dup_box.row(align=True)
                    split = row.split(factor=0.5)
                    split.label(text=f"{label} [{grp_str}]")
                    cols = split.split(factor=0.5)
                    cols.label(text=fix_add)
                    cols.label(text=fix_change)

                # Fix buttons row - aligned with table columns
                btn_row = dup_box.row(align=True)
                split = btn_row.split(factor=0.5)
                # Merge Identical button in first column (Mapping column)
                if _has_identical_mappings(dup["mappings"]):
                    op = split.operator(
                        "chordsong.merge_identical",
                        text="Merge Duplicates",
                        icon="LINKED"
                    )
                    op.conflict_index = idx
                else:
                    split.label(text="")  # Empty space under Mapping column
                # Right side: split into two columns for Apply buttons
                cols = split.split(factor=0.5)
                if fixes_add:
                    op = cols.operator(
                        "chordsong.apply_conflict_fix",
                        text="Apply",
                        icon="CHECKMARK"
                    )
                    op.conflict_index = idx
                    op.conflict_type = "DUPLICATE"
                    op.duplicate_strategy = "ADD"
                else:
                    cols.label(text="")
                if fixes_change:
                    op = cols.operator(
                        "chordsong.apply_conflict_fix",
                        text="Apply",
                        icon="CHECKMARK"
                    )
                    op.conflict_index = idx
                    op.conflict_type = "DUPLICATE"
                    op.duplicate_strategy = "CHANGE_LAST"
                else:
                    cols.label(text="")

                box.separator(factor=0.3)

    def _print_to_console(self):
        """Print detailed report to console."""
        if not self.conflicts:
            return

        total = len(self.conflicts["prefix_conflicts"]) + len(self.conflicts["duplicates"])

        print("\n" + "="*60)
        print("CHORD CONFLICT REPORT")
        print("="*60)

        if self.conflicts["prefix_conflicts"]:
            print(f"\n⚠ PREFIX CONFLICTS ({len(self.conflicts['prefix_conflicts'])})")
            print("-"*60)
            for c in self.conflicts["prefix_conflicts"]:
                print(f"\n  Prefix: '{c['prefix_chord']}' → {c['prefix_label']}")
                print(f"  Blocks: '{c['full_chord']}' → {c['full_label']}")
                print(f"  Context: {c['context']}")

        if self.conflicts["duplicates"]:
            print(f"\n⚠ DUPLICATE CHORDS ({len(self.conflicts['duplicates'])})")
            print("-"*60)
            for d in self.conflicts["duplicates"]:
                print(f"\n  Chord: '{d['chord']}' (Context: {d['context']})")
                print(f"  Found {d['count']} times:")
                for label in d['labels']:
                    print(f"    → {label}")

        print("\n" + "="*60)
        print(f"Total conflicts found: {total}")
        print("="*60 + "\n")

    def _generate_chord(self, base_chord, all_chords, exclude_chord=None, exclude_symbols=None, change_last=False):
        """Unified chord generation function - delegates to shared utility."""
        return generate_chord(base_chord, all_chords, exclude_chord, exclude_symbols, change_last)

    def _find_conflicts(self, mappings):
        """Find all chord conflicts - delegates to shared utility with fixes."""
        return find_conflicts_util(mappings, generate_fixes=True)

def find_conflicts(mappings, generate_fixes=False):
    """Module-level function to find conflicts without needing an operator instance.

    Args:
        mappings: Collection of mapping objects to check
        generate_fixes: If True, generate suggested fixes. Default False for silent checks.
    """
    return find_conflicts_util(mappings, generate_fixes=generate_fixes)
