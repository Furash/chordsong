# Conflict Detection

Identify and resolve chord mapping conflicts.

## Overview

Chord conflicts occur when mappings interfere with each other, preventing proper execution.

## Types of Conflicts

### Prefix Conflicts

A prefix conflict occurs when one chord sequence is a complete starting part of another. 

**Example:**
- Mapping A: `g` (Frame Selected)
- Mapping B: `g g` (Frame All)

Because Chord Song executes an action as soon as an exact match is found, pressing `g` would trigger Mapping A immediately. Mapping B (`g g`) becomes **unreachable** because the sequence is "stolen" by the shorter chord.

### Duplicate Mappings

Duplicate conflicts occur when the exact same key sequence is assigned to multiple actions in the same **[Context](../concepts/chord_mappings.md#context)**.

**Example:**
- Mapping A: `f r` → Action: "Reset Factory Settings"
- Mapping B: `f r` → Action: "Recover Autosave"

While Chord Song will allow these to exist in your configuration, it will only ever execute the first one it finds in its internal list, leading to unpredictable behavior.

## Checking for Conflicts

Chord Song includes a built-in **Conflict Checker** to keep your mappings clean and functional.

1.  Open the Chord Song preferences.
2.  Click the **Check Conflicts** button (or run `chordsong.check_conflicts` from the search menu).
3.  A dialog will appear listing all identified issues.
4.  The addon also prints a detailed report to the **System Console** for easier review of large mapping sets.

## Resolving Conflicts

When a conflict is detected, you have several strategies to resolve it:

### 1. Manual Modification
You can simply edit the "Chord" field of one of the conflicting mappings in the preferences tab to a unique sequence.

### 2. Automatic Fixes
The Conflict Checker provides suggested fixes that you can apply with a single click:

| Strategy | Description |
| :--- | :--- |
| **Add Symbol** | Appends a unique letter or number to the end of the chord (e.g., `g` → `g a`). |
| **Change Last** | Swaps the final key of the sequence for a non-conflicting alternative (e.g., `g g` → `g f`). |

## Automatic Suggestions

The suggestion engine is context-aware. When generating a fix, it:
1.  Scans the alphabet (`a-z`) and numbers (`0-9`).
2.  Filters out any keys that would create *new* prefix or duplicate conflicts.
3.  Prioritizes simple, single-character additions to keep sequences short.
4.  Ensures that if multiple duplicates are fixed at once, they each receive a unique recommendation.
