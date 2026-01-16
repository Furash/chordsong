# Import & Export

Configuration operations for chord mappings.

![Import & Export](/chordsong/scr/prefs_config.png)

!!! tip "Quick Sharing"
    For sharing small chord snippets, use [Copy & Paste](chord_serialization.md) instead. Import/Export is designed for complete configuration management.

## Operations

- **Save Config**: Overwrites the current Config file with the current configuration.
- **Export Config**: Exports selected groups only (leader key excluded)
- **Load Config**: Imports configuration from the current Config Path.
- **Append Config**: Merges configuration (preserves existing, runs conflict checker)
- **Load Default Config**: Loads default configuration.
- **Restore Autosave**: Restores from `.autosave.json` (see [Autosave](autosave.md))

## Save Config

- If config path set: Saves directly to that file
- Otherwise saves into the extension-specific user directory: *chordsong.json*

## Export Config

![Export Config](/chordsong/scr/export_config.png)

Exports selected group mappings.

**Process**:

1. Validates JSON and config structure
2. Suspends autosave
3. Adds mappings (does not clear existing)
4. Adds groups (only if name doesn't exist)
5. Preserves settings (overlay, scripts folder, leader key)
6. Runs conflict checker automatically

**Validation**: Checks JSON validity, config structure, version compatibility. Shows warnings but proceeds.

**Conflicts**: Duplicate chords and prefix conflicts detected automatically.

## Configuration File Format

### Location

**Default**: Extension-specific user directory (`chordsong.json`)

The default configuration file is stored in the extension's user directory, which persists between extension upgrades. This directory is managed by Blender and is specific to the Chord Song extension.

**Custom Path**: Set in preferences. When set:

- Save Config saves directly (no browser)
- Load Config loads directly (if file exists)
- Autosave creates `.autosave.json` in same directory

### Manual Editing

Configuration files can be edited directly.

### Mapping structure example

```json
"mappings": [
   {
      "enabled": true,
      "chord": "a 1",
      "label": "Cube",
      "icon": "",
      "group": "Mesh",
      "context": "VIEW_3D",
      "mapping_type": "OPERATOR",
      "operators": [
            {
               "operator": "mesh.primitive_cube_add",
               "call_context": "INVOKE_DEFAULT",
               "kwargs": {}
            }
      ]
   },
```
