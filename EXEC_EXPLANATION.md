# Explanation: Use of `exec()` in Chord Song

## Summary

Chord Song uses `exec()` **only** to execute Python scripts that users explicitly configure themselves. The add-on does not execute any arbitrary code automatically or by default.

## How Script Execution Works

1. **User-Initiated Configuration**: Users must manually create "Script Mappings" in the add-on preferences, explicitly pointing to specific Python files on their system.

2. **Explicit User Action Required**: Scripts are only executed when:
   - A user triggers a chord sequence they have personally mapped to a script
   - The user has explicitly configured that mapping to point to a specific Python file

3. **No Automatic Execution**: The add-on never executes code automatically. There are no hardcoded scripts or automatic script execution.

## Code Flow

The `exec()` calls occur in two places:

1. **`operators/leader.py`** (lines 618, 621, 623): Executes a script file when a user triggers a chord that they have mapped to that specific script file.

2. **`utils/render.py`** (lines 345, 348, 350): Re-executes scripts from history entries, which were originally created by user-configured mappings.

## User Control

- Users must explicitly create script mappings in Preferences → Chord Song → Mappings
- Users must manually specify the path to each Python file they want to execute
- Users can review and audit all scripts before mapping them to chords
- The add-on documentation explicitly warns users to only map scripts they have written or audited

## Security Model

The add-on follows a **user-controlled execution model**:
- The add-on provides a mechanism for users to execute their own scripts
- Users are responsible for the scripts they choose to execute
- No scripts are bundled with the add-on that get executed automatically
- The `exec()` function is used as a necessary mechanism to execute user-provided Python files, similar to how Blender's own script execution works

## Conclusion

The use of `exec()` is entirely user-controlled. Users explicitly choose which scripts to execute by configuring mappings. The add-on does not execute any code without explicit user configuration and action.
