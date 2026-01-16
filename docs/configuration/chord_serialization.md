# Chord Serialization (Copy/Paste)

Chord Song supports **atomic chord serialization** for easy sharing and backup of chord snippets. This feature enables you to copy selected chord mappings to your clipboard and paste them into another configuration or share them with others.

<!-- markdownlint-disable MD033 -->
<video autoplay loop muted playsinline>
  <source src="/chordsong/scr/chords_copy_paste.mp4" type="video/mp4">
</video>
<!-- markdownlint-enable MD033 -->

!!! info "Full Configuration Management"
    For complete configuration backup and restore, use [Import & Export](import_export.md). Copy/Paste is designed for quick sharing of specific chords.

## Overview

The serialization format uses **compact JSON** designed to be:

- **Minimal and human-readable**: Easy to inspect and understand
- **Validatable**: Clear structure with version tracking
- **Forward-compatible**: Designed to handle future format changes
- **Atomic**: Can represent single chords or sequences

## Copy/Paste Operations

### Selecting Chords

Each chord mapping has a checkbox on the left side that allows you to select it for copy operations:

1. **Individual Selection**: Click the checkbox next to any chord to select/deselect it
2. **Select All**: Click the "Select All" button to select all visible chords in the current context
3. **Deselect All**: Click the "Deselect All" button to clear all selections

### Copying Chords

There are two ways to copy chords:

1. **Copy Selected**: Select one or more chords using checkboxes, then click "Copy Selected"
2. **Copy Single**: Click the copy icon (📋) next to any chord to copy just that chord

The chord data is copied to your clipboard as JSON.

### Pasting Chords

1. Copy chord data to your clipboard (from Chord Song or another source)
2. Click the "Paste" button
3. The chords will be added to your current configuration
4. A conflict check runs automatically to detect any duplicate chord sequences

## JSON Format

### Structure

```json
{
  "version": 1,
  "chords": [
    {
      "chord": "g g",
      "label": "Frame Selected",
      "icon": "󰆾",
      "group": "View",
      "context": "VIEW_3D",
      "mapping_type": "OPERATOR",
      "enabled": true,
      "operator": "view3d.view_selected",
      "call_context": "EXEC_DEFAULT"
    }
  ]
}
```

### Required Fields

Every chord must have:

- `chord`: The key sequence (e.g., `"g g"`)
- `mapping_type`: One of `OPERATOR`, `PYTHON_FILE`, `CONTEXT_PROPERTY`, or `CONTEXT_TOGGLE`

### Optional Common Fields

- `label`: Display name (default: empty)
- `icon`: Nerd Font icon (default: empty)
- `group`: Category name (default: "Ungrouped")
- `context`: Editor context (default: `"VIEW_3D"`)
- `enabled`: Whether the chord is active (default: `true`)

### Mapping Type-Specific Fields

#### Operator Mappings

```json
{
  "mapping_type": "OPERATOR",
  "operator": "view3d.view_selected",
  "call_context": "EXEC_DEFAULT",
  "kwargs_json": "use_all_regions=False"
}
```

- `operator`: Blender operator ID
- `call_context`: `"EXEC_DEFAULT"` or `"INVOKE_DEFAULT"`
- `kwargs_json`: Optional operator parameters
- `sub_operators`: Optional array of additional operators to chain

#### Script Mappings

```json
{
  "mapping_type": "PYTHON_FILE",
  "python_file": "/path/to/script.py",
  "kwargs": {
    "param1": "value1",
    "param2": 42
  }
}
```

- `python_file`: Path to Python script
- `kwargs`: Optional parameters dict (keys prefixed with `_` start new rows)

#### Property Mappings

```json
{
  "mapping_type": "CONTEXT_PROPERTY",
  "context_path": "space_data.shading.type",
  "property_value": "'SOLID'",
  "sub_items": [
    {
      "path": "space_data.shading.light",
      "value": "'STUDIO'"
    }
  ]
}
```

- `context_path`: Property path
- `property_value`: Value to set (Python expression)
- `sub_items`: Optional array of additional properties

#### Toggle Mappings

```json
{
  "mapping_type": "CONTEXT_TOGGLE",
  "context_path": "space_data.overlay.show_face_orientation",
  "sync_toggles": false,
  "sub_items": [
    {
      "path": "space_data.overlay.show_wireframes"
    }
  ]
}
```

- `context_path`: Toggle property path
- `sync_toggles`: Whether to sync all sub-toggles (default: `false`)
- `sub_items`: Optional array of additional toggles

## Use Cases

### Sharing Chord Presets

Share your favorite chord configurations with others:

1. Select the chords you want to share
2. Click "Copy Selected"
3. Paste the JSON into a text file, Discord, GitHub, etc.
4. Others can copy the JSON and use "Paste" to add them

### Backup Specific Chords

Quickly backup important chords before experimenting:

1. Select the chords you want to backup
2. Click "Copy Selected"
3. Save the JSON to a text file

### Migrating Between Contexts

Copy chords from one context to another:

1. Switch to the source context tab
2. Select and copy the chords
3. Switch to the target context tab
4. Paste the chords
5. The chords will be added with their original context, or you can edit them

## Validation

When pasting chords, the system validates:

- JSON syntax
- Required fields presence
- Mapping type validity
- Version compatibility

Warnings are shown for any issues, but the paste operation continues for valid chords.

## Conflict Detection

After pasting, the conflict checker runs automatically to detect:

- **Duplicate chords**: Same chord sequence in the same context
- **Prefix conflicts**: One chord is a prefix of another (e.g., `g` and `g g`)

Conflicted chords are highlighted in red in the UI.
