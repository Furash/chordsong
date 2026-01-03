"""Operator to check for chord mapping conflicts."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

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
        if prefs_ctx:
            try:
                with bpy.context.temp_override(**prefs_ctx):
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
    suffix_list = "xyzuvwabcdefghijklmnopqrt0123456789"
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
    
    Args:
        mappings: Collection of mapping objects to check
        generate_fixes: If True, generate suggested fixes (expensive). If False, only detect conflicts.
    
    Returns a dict with 'prefix_conflicts' and 'duplicates' lists.
    """
    conflicts = {"prefix_conflicts": [], "duplicates": []}
    by_context = {}
    
    for m in mappings:
        if not getattr(m, "enabled", True):
            continue
        ctx = getattr(m, "context", "VIEW_3D")
        by_context.setdefault(ctx, []).append(m)

    for ctx, ctx_mappings in by_context.items():
        chord_map = {}
        all_chords = []

        for m in ctx_mappings:
            chord_str = get_str_attr(m, "chord")
            tokens = split_chord(chord_str)
            if not tokens:
                continue

            all_chords.append(chord_str)
            chord_key = tuple(tokens)
            chord_map.setdefault(chord_key, []).append(m)

        # Check for duplicates
        for chord_key, mappings_list in chord_map.items():
            if len(mappings_list) > 1:
                base_chord = " ".join(chord_key)
                
                conflict_data = {
                    "chord": base_chord,
                    "context": ctx,
                    "count": len(mappings_list),
                    "labels": [get_str_attr(m, "label") for m in mappings_list],
                    "groups": [get_str_attr(m, "group") for m in mappings_list],
                    "mappings": mappings_list,
                }
                
                # Only generate fixes if requested (expensive operation)
                if generate_fixes:
                    fixes = {"add": [], "change_last": []}
                    base_key = chord_key
                    
                    for strategy in fixes:
                        # CRITICAL: When generating fixes for a duplicate set, 
                        # we must NOT check against the duplicates themselves,
                        # otherwise the existing chord will block many potential fixes.
                        temp_chords = [c for c in all_chords if tuple(split_chord(c)) != base_key]
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

        # Check for prefix conflicts
        chord_keys = list(chord_map.keys())
        for i, chord1 in enumerate(chord_keys):
            for chord2 in chord_keys[i+1:]:
                if len(chord1) < len(chord2) and chord2[:len(chord1)] == chord1:
                    prefix_key, full_key = chord1, chord2
                elif len(chord2) < len(chord1) and chord1[:len(chord2)] == chord2:
                    prefix_key, full_key = chord2, chord1
                else:
                    continue

                prefix_chord = " ".join(prefix_key)
                full_chord = " ".join(full_key)

                conflict_data = {
                    "prefix_chord": prefix_chord,
                    "prefix_label": get_str_attr(chord_map[prefix_key][0], "label"),
                    "prefix_group": get_str_attr(chord_map[prefix_key][0], "group"),
                    "full_chord": full_chord,
                    "full_label": get_str_attr(chord_map[full_key][0], "label"),
                    "full_group": get_str_attr(chord_map[full_key][0], "group"),
                    "context": ctx,
                    "prefix_mapping": chord_map[prefix_key][0],
                }
                
                # Only generate fix if requested
                if generate_fixes:
                    conflict_data["suggested_fix"] = generate_chord(prefix_chord, all_chords, exclude_chord=full_chord)

                conflicts["prefix_conflicts"].append(conflict_data)

    return conflicts

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
        conflicts = CHORDSONG_OT_CheckConflicts._conflicts
        if not conflicts:
            self.report({"WARNING"}, "No conflicts data available")
            return {"CANCELLED"}

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
            CHORDSONG_OT_CheckConflicts._conflicts = new_conflicts
            
            # Also update the in-place lists if someone is holding a reference to the old dict
            if conflicts:
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
            
            # Redraw all windows
            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()
            return None

        bpy.app.timers.register(delayed_refresh, first_interval=0.1)
        return {"FINISHED"}

class CHORDSONG_OT_CheckConflicts(bpy.types.Operator):
    """Check for chord mapping conflicts (prefixes and duplicates)"""

    bl_idname = "chordsong.check_conflicts"
    bl_label = "Check Chord Conflicts"
    bl_options = {"REGISTER"}

    _conflicts = None
    _recheck_pending = False
    _prefs_context = None
    _popup_region = None

    def invoke(self, context: bpy.types.Context, event):  # pylint: disable=unused-argument
        """Show dialog with conflicts."""
        p = prefs(context)

        self._conflicts = self._find_conflicts(p.mappings)
        CHORDSONG_OT_CheckConflicts._conflicts = self._conflicts

        # Store preferences context for re-running
        prefs_context = {}
        if hasattr(context, "area") and context.area and context.area.type == "PREFERENCES":
            for key in ("area", "region", "space_data"):
                val = getattr(context, key, None)
                if val:
                    prefs_context[key] = val
        CHORDSONG_OT_CheckConflicts._prefs_context = prefs_context or None

        if not self._conflicts["prefix_conflicts"] and not self._conflicts["duplicates"]:
            self.report({"INFO"}, "No chord conflicts found! ✓")
            CHORDSONG_OT_CheckConflicts._conflicts = None
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
        conflicts = CHORDSONG_OT_CheckConflicts._conflicts
        if not conflicts:
            return

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
                # Fix button with suggested chord
                op = row.operator(
                    "chordsong.apply_conflict_fix",
                    text=f"→ {conflict['suggested_fix']}",
                    icon="CHECKMARK"
                )
                op.conflict_index = idx
                op.conflict_type = "PREFIX"

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
                split.label(text="")  # Empty space under Mapping column
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
        if not self._conflicts:
            return

        total = len(self._conflicts["prefix_conflicts"]) + len(self._conflicts["duplicates"])

        print("\n" + "="*60)
        print("CHORD CONFLICT REPORT")
        print("="*60)

        if self._conflicts["prefix_conflicts"]:
            print(f"\n⚠ PREFIX CONFLICTS ({len(self._conflicts['prefix_conflicts'])})")
            print("-"*60)
            for c in self._conflicts["prefix_conflicts"]:
                print(f"\n  Prefix: '{c['prefix_chord']}' → {c['prefix_label']}")
                print(f"  Blocks: '{c['full_chord']}' → {c['full_label']}")
                print(f"  Context: {c['context']}")

        if self._conflicts["duplicates"]:
            print(f"\n⚠ DUPLICATE CHORDS ({len(self._conflicts['duplicates'])})")
            print("-"*60)
            for d in self._conflicts["duplicates"]:
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
