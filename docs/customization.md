# Customization

Make Chord Song truly yours by customizing its behavior and appearance.

## Preference Settings

The preferences are divided into two main tabs: **Mappings** and **UI**.

### Behavior Settings
Control how Chord Song interacts with your input:

- **Overlay**: Toggle the main which-key style overlay on or off.
- **Fading Overlay**: Enable a brief visual confirmation (notification) after a chord is executed.
- **Scripts Folder**: Define a default directory for your Python scripts to enable quick selection when creating mappings.
- **Folder Style**: Choose how prefix items (folders leading to more chords) are displayed:
    - *Default*: Show only the number of keymaps.
    - *Groups First*: Show a list of unique groups followed by the keymap count (recommended).
    - *Hybrid*: A compact mix of groups and counts.

### UI Settings

- **Max Items**: Limit the number of items shown per column.
- **Column Layout**: Control the number of rows before wrapping to a new column.
- **Font Sizes**: Independently scale headers, body text, chord tokens, and the footer.
- **Colors & Opacity**: Customize every element's color, including toggle states, icons, and background panels.
- **Positioning**: Anchor the overlay to any corner or center edge. Use fine-tuned **X/Y Offsets** for perfect placement.
- **Animation**: Enable or disable the **Fading Overlay**, which provides a brief visual confirmation of the executed action.

## Configuration Management

Chord Song's entire configuration—mappings and groups—is stored in a single JSON file. This makes it easy to back up, share, or sync across multiple Blender installations.

### Config Path
You can specify a custom **Config Path** in the preferences. By default, it uses a standard location in your Blender user scripts directory:
`.../scripts/presets/chordsong/chordsong.json`

### Import & Export
Use the **Load** and **Save** buttons to manually manage your configuration files. This is useful for:
- Sharing your setup with others.
- Switching between different mapping profiles.
- Recovering from a manual edit of the JSON file.

### Autosave System
To prevent data loss, Chord Song includes an **Autosave** mechanism. 
- **Debounced Saving**: Every time you change a mapping, icon, or group, a background timer is started.
- **Efficiency**: If you make multiple changes quickly, the timer resets, only performing the actual write once you stop editing for 5 seconds.
- **Quiet Operation**: Autosave happens in the background without interrupting your workflow.

