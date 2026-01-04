# Conflict Detection

Identify and resolve chord mapping conflicts.

## Types of Conflicts

### Prefix Conflicts

Occurs when one chord sequence is a prefix of another.

**Example:**

- Mapping A: `g` (Frame Selected)
- Mapping B: `g g` (Frame All)

Pressing `g` triggers Mapping A immediately, making Mapping B unreachable.

### Duplicate Mappings

The same key sequence assigned to multiple actions in the same **[Context](../concepts/chord.md#context)**.

**Example:**

- Mapping A: `f r` → "Reset Factory Settings"
- Mapping B: `f r` → "Recover Autosave"

Only the first mapping executes, leading to unpredictable behavior.

## Checking for Conflicts

1. Open Chord Song preferences.
2. Click **Check Conflicts** (or run `chordsong.check_conflicts`).
3. Review the dialog and System Console report.

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/conflict_checker.png" alt="Check Conflicts" width="500">
<!-- markdownlint-enable MD033 -->

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/conflict_ui.png" alt="Check Conflicts Report">
<!-- markdownlint-enable MD033 -->

## Resolving Conflicts

### Manual Modification

Edit the "Chord" field of one conflicting mapping to a unique sequence.

### Automatic Fixes

The Conflict Checker suggests fixes:

| Strategy | Description |
| :--- | :--- |
| **Add Symbol** | Appends a unique letter or number (e.g., `g` → `g a`). |
| **Change Last** | Swaps the final key (e.g., `g g` → `g f`). |

## Suggestion Algorithm

When generating a fix, it will:

- Filter keys that would create new conflicts.
- Prefer single-character additions.
- Ensure unique recommendations for multiple duplicates.
