# Autosave

Chord Song automatically saves your configuration to prevent data loss. The autosave system uses a debounced timer that waits for a period of inactivity before writing the configuration to disk.

## Autosave Behavior

The autosave system uses **debouncing** to prevent excessive file writes. When a change is detected, a timer is scheduled. If another change occurs before the timer fires, the timer is reset.

This means if you're actively editing your mappings, autosave won't trigger until you've stopped making changes for 5 seconds. This prevents performance issues from frequent file writes during rapid editing.

## Autosave File Location

The autosave file is saved next to your main configuration file with the `.autosave.json` extension.

### Default Location

If you haven't set a custom config path, the default location is in the extension-specific user directory:

```
chordsong.json
```

```
chordsong.autosave.json
```

The extension-specific user directory persists between extension upgrades and is managed by Blender. This ensures your configuration and autosave files are preserved when you update the extension.

### Custom Config Path

If you've set a custom **Config Path** in preferences, the autosave file will be created in the same directory as your config file, with `.autosave` inserted before the `.json` extension.

For example:

- Config: `C:\configs\my_chords.json`
- Autosave: `C:\configs\my_chords.autosave.json`

For more information about configuration file locations and formats, see [Import & Export](import_export.md#configuration-file-format).

## Restoring from Autosave

If something goes wrong, you can restore from the autosave file using the **Restore Autosave** operator (available in the Config section of preferences). This loads the `.autosave.json` file associated with your current config path.


For information about manual save/load operations, see [Import & Export](import_export.md).
