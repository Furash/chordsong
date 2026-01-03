# Autosave

Automatic saving of your chord mappings.

## Overview

Chord Song automatically saves your configuration to prevent data loss. The autosave system uses a debounced timer that waits for a period of inactivity before writing the configuration to disk.

## Autosave Behavior

The autosave system uses **debouncing** to prevent excessive file writes. When a change is detected, a timer is scheduled. If another change occurs before the timer fires, the timer is reset.

- **Default delay**: 3 seconds (internal default)
- **Typical delay**: 5 seconds (used by most operations)
- **Behavior**: The timer resets on each change, so rapid edits only trigger one save after you stop making changes

This means if you're actively editing your mappings, autosave won't trigger until you've stopped making changes for 5 seconds. This prevents performance issues from frequent file writes during rapid editing.

## Configuration File Location

The autosave file is saved **next to your main configuration file** with the `.autosave.json` extension.

- **Main config**: `chordsong.json`
- **Autosave file**: `chordsong.autosave.json` (same directory)

### Default Location

If you haven't set a custom config path, the default location is:

```
<Blender User Scripts>/presets/chordsong/chordsong.json
```

The autosave file will be at:

```
<Blender User Scripts>/presets/chordsong/chordsong.autosave.json
```

You can find your Blender user scripts directory by going to **Edit → Preferences → File Paths → Scripts**.

### Custom Config Path

If you've set a custom **Config Path** in preferences, the autosave file will be created in the same directory as your config file, with `.autosave` inserted before the `.json` extension.

For example:
- Config: `C:\configs\my_chords.json`
- Autosave: `C:\configs\my_chords.autosave.json`

## What Triggers Autosave

Autosave is triggered automatically when:

1. **Preference changes**: Any modification to addon preferences (config path, scripts folder, overlay settings, etc.)
2. **Mapping changes**: Editing any property of a chord mapping (chord sequence, label, operator, icon, etc.)
3. **Mapping operations**:
   - Adding a new mapping
   - Removing a mapping
   - Duplicating a mapping
4. **Group operations**:
   - Adding a group
   - Removing a group
   - Renaming a group
   - Group cleanup operations
5. **Other operations**:
   - Selecting an icon for a mapping
   - Selecting a script for a mapping
   - Conflict checking operations
   - Context menu operations

Autosave is **suspended** during manual load operations to prevent overwriting the file you're loading.

## Manual Save/Load

While autosave handles most cases automatically, you can manually save or load configurations:

### Manual Save

Use the **Save User Config** operator (available in the preferences UI) to:
- Save your current configuration to a specific file
- Set a custom config path
- Export your configuration for backup or sharing

If you already have a config path set, it will save directly to that file. Otherwise, it will open a file browser to choose a location.

### Manual Load

Use the **Load User Config** operator to:
- Load a configuration from a JSON file
- Switch between different configuration profiles
- Import configurations from backups or other users

### Restore Autosave

If something goes wrong, you can restore from the autosave file using the **Restore Autosave** operator. This loads the `.autosave.json` file associated with your current config path.

## Loading Default Configuration

You can reset your configuration to the default Chord Song mappings using the **Load Default Chord Song Config** operator. This loads the default configuration from `ui/default_mappings.json` that ships with the addon.

This is useful if you want to start fresh or see what the default mappings look like.

## Configuration Format

Both the main config file and autosave file use the same JSON format. The configuration includes:

- **Mappings**: Array of chord mapping objects with properties like `chord`, `label`, `operator`, `context`, etc.
- **Groups**: Array of group definitions
- **Preferences**: Various addon settings

The JSON is formatted with indentation (2 spaces for autosave, 4 spaces for manual saves) and uses UTF-8 encoding to support international characters.

You can edit these files directly if needed, but be careful to maintain valid JSON syntax. The autosave file is automatically overwritten, so manual edits to it will be lost.
