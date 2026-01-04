# Toggle Mappings

**Toggle Mappings** allow you to flip properties (On/Off) using chords (e.g., toggle `space_data.overlay.show_wireframe`).

Unlike [Property Mappings](property.md), toggle mappings flip the state each time they're activated rather than setting a fixed value.

## Adding Toggles

- **Preferences**: Manually add and edit toggle mappings in the Chord Song tab.
- **Context Menu**: Right-click any checkbox or boolean property in Blender's UI and select **Add Chord Mapping**.
- **Info Panel**: Extract toggle actions from Blender's history for batch creation.

## Chaining & "Sync Toggles"

You can bind multiple toggles to a single chord to create "Presets" (e.g., one chord that toggles text and statistics at once).

<!-- markdownlint-disable MD033 -->
<img src="../../../scr/toggle_presets.png" alt="Toggle Presets">
<!-- markdownlint-enable MD033 -->

## Toggle State Overlay

The state of the toggle is displayed in the overlay.
<!-- markdownlint-disable MD033 -->
<img src="../../../scr/toggle_overlay.png" alt="Toggle State Overlay" width="400">
<!-- markdownlint-enable MD033 -->

### The "Checker Board" Problem

When multiple toggles are bound to one chord, they can get out of sync (e.g., Text is ON but Statistics is OFF). Pressing the chord would flip both, keeping them out of sync indefinitely.

### The Sync Solution

Enable the **Sync** button (chain icon) on a mapping with multiple toggles to solve this:

- **Enabled**: When pressed, all sub-toggles will match the state of the **primary** (first) toggle. On the first press, everything "snaps" to a unified state (all ON or all OFF), preventing the checker board effect.
