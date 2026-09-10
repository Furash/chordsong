# Property Mappings

**Property Mappings** allow you to set a Blender property to a specific value using chords (e.g., set `space_data.shading.type` to `'SOLID'`).

Unlike [Toggle Mappings](toggle.md), property mappings set a fixed value rather than flipping a boolean state.

## Adding Properties

- **Preferences**: Manually add and edit property mappings in the Chord Song tab.
- **Context Menu**: Right-click any property field (checkboxes, sliders, dropdowns) and select **Add Chord Mapping**.
- **Info Panel**: Extract property assignments from Blender's history for batch creation.

## Addon Preference Paths

Paths may contain bracket lookups, so add-on preferences can be bound like any
other property:

```text
preferences.addons["bl_ext.user_default.UniV"].preferences.use_trims
```

Right-clicking a checkbox or field inside an add-on's preferences panel (or a
panel that draws its preferences) fills this path in automatically. The key in
brackets is the add-on's module name as listed in
`bpy.context.preferences.addons.keys()`.

## Chaining Multiple Properties

You can bind multiple properties to a single chord to create "Presets" (e.g., one chord that sets Camera FOV, Clip Start, and Clip End at once).

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/property_presets.png" alt="Property Chain">
<!-- markdownlint-enable MD033 -->

## Configuration Properties

- **Property**: The internal path to the property (e.g., `space_data.shading.type`).
- **Value**: The specific value to set (e.g., `0.5`, `'SOLID'`, or `'WIREFRAME'`).
- **Sub-Items**: Use the **+** button to add additional properties to the same chord.
