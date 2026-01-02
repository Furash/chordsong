# Property Mappings

**Property Mappings** allow you to directly set or toggle a Blender setting (e.g., `space_data.overlay.show_wireframe`) using chords. 

- **Toggles**: Used for boolean (On/Off) settings. Every activation flips the state.
- **Properties**: Used to set a specific value (e.g., set `shading.type` to `'SOLID'`).

## Adding Properties

1. **Context Menu (RMB)**: Right-click any property field (checkboxes, sliders, dropdowns) and select **Add Chord Mapping**.
2. **Preferences Panel**: Manually enter the **Context Path** in the mapping entry.
3. **Info Panel**: Extract property assignments from your history.

## Chaining & "Sync Toggles"

You can bind multiple properties to a single chord to create "Layout Presets" (e.g., one chord that toggles wireframe, face orientation, and statistics at once).

### The "Checker Board" Problem
When multiple toggles are bound to one chord, they can get out of sync (e.g., Wireframe is ON but Statistics is OFF). Pressing the chord would flip both, keeping them out of sync indefinitely.

### The Sync Solution
Enable the **Sync** button (blue icon) on a mapping with multiple toggles to solve this:
- **Enabled**: When pressed, all sub-properties will match the state of the **primary** (first) property.
- **Result**: On the first press, everything "snaps" to a unified state (all ON or all OFF), preventing the checker board effect.

## Configuration Properties

| Property | Description |
| :--- | :--- |
| **Context Path** | The internal path to the property (e.g., `space_data.shading.type`). |
| **Value** | (Property type only) The specific value to set (e.g., `0.5` or `'WIREFRAME'`). |
| **Sub-Items** | Use the **+** button to add additional properties to the same chord. |
| **Sync (Toggle)** | Ensures all sub-items match the primary item's state. |
