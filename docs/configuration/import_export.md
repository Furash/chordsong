# Import & Export

Share and backup your chord mappings.

## Overview

Chord Song supports importing and exporting configurations as JSON files. This allows you to:

- **Backup** your chord mappings and settings
- **Share** configurations with other users
- **Switch** between different configuration profiles
- **Restore** previous configurations if something goes wrong

## Exporting Configuration

To export your current configuration:

1. Open **Edit → Preferences → Add-ons**
2. Find **Chord Song** and expand it
3. In the **Config** section, click **Save Config**

### Export Behavior

- **If you have a config path set**: The configuration is saved directly to that file without opening a file browser
- **If no config path is set**: A file browser opens, defaulting to `<Blender User Scripts>/presets/chordsong/chordsong.json`

After saving, the **Config Path** preference is automatically updated to point to the saved file. This means future saves (and autosaves) will use this location.

### What Gets Exported

The exported JSON file includes:

- **All chord mappings**: Complete mapping definitions with chords, labels, operators, icons, groups, contexts, etc.
- **Groups**: All group definitions with their display order and expanded state
- **Overlay settings**: All overlay customization options (colors, fonts, positions, etc.)
- **Scripts folder**: The configured scripts folder path
- **Leader key**: The current leader key setting
- **Configuration version**: Version number for compatibility checking

The file is saved with 4-space indentation and UTF-8 encoding to support international characters.

## Importing Configuration

To import a configuration from a JSON file:

1. Open **Edit → Preferences → Add-ons**
2. Find **Chord Song** and expand it
3. In the **Config** section, click **Load Config**

### Import Behavior

- **If you have a config path set and the file exists**: The configuration loads directly from that file
- **Otherwise**: A file browser opens to select a JSON file

After loading, the **Config Path** preference is updated to point to the loaded file.

### Import Process

When importing:

1. **Autosave is suspended** during the import to prevent overwriting the file you're loading
2. **Existing mappings and groups are cleared** and replaced with the imported data
3. **Preferences are updated** with the imported settings
4. **Warnings may be shown** for:
   - Unsupported configuration versions
   - Unknown leader key values
   - Other compatibility issues

Up to 5 warnings are displayed in the Blender status bar. The import will still succeed even if warnings are shown, but some settings may not be applied.

### Version Compatibility

Chord Song supports:
- **Version 2** (current): Full feature support including operator chains, script parameters, and all overlay settings
- **Version 1** (legacy): Backward compatibility for older configuration files

If you import a configuration with an unsupported version, a warning will be shown, but the import will attempt to proceed.

## Appending Configuration

**Append Config** allows you to merge another configuration file with your current configuration **without losing your existing mappings and settings**. This is the recommended way to combine configurations from multiple sources.

### When to Use Append

Use **Append Config** when you want to:
- **Add mappings** from another user's configuration while keeping your own
- **Merge configurations** from multiple sources
- **Import specific mappings** without replacing your entire setup
- **Preserve your settings** (overlay, scripts folder, leader key) while adding new mappings

### How to Append

To append a configuration:

1. Open **Edit → Preferences → Add-ons**
2. Find **Chord Song** and expand it
3. In the **Config** section, click **Append Config**
4. Select the JSON configuration file you want to merge

### Append Behavior

When appending a configuration:

1. **Autosave is suspended** during the append operation
2. **All mappings from the new file are added** to your existing mappings (nothing is cleared)
3. **New groups are added** only if they don't already exist (by name)
4. **Your current settings are preserved**:
   - Overlay settings (colors, fonts, positions, etc.) remain unchanged
   - Scripts folder path remains unchanged
   - Leader key remains unchanged
5. **Conflict Checker automatically runs** after appending to detect:
   - Duplicate chord sequences
   - Prefix conflicts (where one chord is a prefix of another)
6. **Warnings may be shown** for unsupported configuration versions

### What Gets Merged

- ✅ **Mappings**: All mappings from the appended file are added to your existing mappings
- ✅ **Groups**: Groups are added only if they don't already exist (by name)
- ❌ **Settings**: Your overlay settings, scripts folder, and leader key are **not** changed

### Conflict Detection

After appending, the **Conflict Checker** automatically opens to help you resolve any conflicts:

- **Duplicate chords**: If the appended config contains chords that already exist in your configuration, you'll see duplicates listed
- **Prefix conflicts**: If a chord in the appended config is a prefix of an existing chord (or vice versa), this will be flagged

You can use the Conflict Checker UI to:
- Review all conflicts
- Remove duplicate mappings
- Rename conflicting chords
- Resolve prefix conflicts

### Example Use Case

1. You have your own custom configuration with 20 mappings
2. A friend shares their configuration with 15 different mappings
3. You use **Append Config** to merge their file
4. You now have 35 mappings total (your 20 + their 15)
5. Your overlay settings, scripts folder, and leader key remain unchanged
6. Conflict Checker runs automatically to catch any duplicates or conflicts
7. You resolve any conflicts using the Conflict Checker UI

### Version Compatibility

Append Config supports the same version compatibility as regular import:
- **Version 2** (current): Full feature support
- **Version 1** (legacy): Backward compatibility

If you append a configuration with an unsupported version, a warning will be shown, but the append will attempt to proceed.

## Configuration Sharing

JSON configuration files are portable and can be easily shared:

### Sharing Your Configuration

1. **Export your configuration** using **Save Config**
2. **Share the JSON file** via:
   - Email attachment
   - Cloud storage (Google Drive, Dropbox, etc.)
   - Version control (GitHub, GitLab, etc.)
   - Community forums or Discord servers
   - Direct file transfer

### Using Shared Configurations

You have two options when using a shared configuration:

**Option 1: Replace your configuration** (Load Config)
1. **Download** the shared JSON file
2. **Import it** using **Load Config** and selecting the downloaded file
3. Your existing configuration will be replaced entirely

**Option 2: Merge with your configuration** (Append Config) - Recommended
1. **Download** the shared JSON file
2. **Append it** using **Append Config** and selecting the downloaded file
3. Your existing mappings and settings are preserved, and new mappings are added
4. **Resolve conflicts** using the automatically-opened Conflict Checker

**After importing/appending:**
- **Adjust paths** if needed:
  - If the configuration references scripts, update the **Scripts Folder** path to match your system
  - Script paths in mappings are stored as-is, so they may need adjustment if the original user had a different folder structure

### Tips for Sharing

- **Include a README**: Document what the configuration does, what scripts it requires, and any special setup instructions
- **Bundle scripts**: If your configuration uses custom Python scripts, include them in a zip file along with the JSON
- **Test first**: Try importing your own exported configuration to ensure it works correctly
- **Version note**: Mention which version of Chord Song the configuration was created with

## Backup Strategies

Regular backups protect your chord mappings from data loss:

### Manual Backups

1. **Periodic exports**: Regularly use **Save Config** to create backups
2. **Version naming**: Use descriptive filenames like `chordsong_backup_2024-01-15.json`
3. **Multiple locations**: Store backups in:
   - Cloud storage (automatic sync)
   - External drives
   - Version control repositories
   - Email attachments to yourself

### Automatic Backups

- **Autosave**: Chord Song automatically saves to `.autosave.json` files (see [Autosave](autosave.md))
- **Blender's backup**: Blender itself may create backup files in some scenarios

### Backup Best Practices

- **Before major changes**: Export before experimenting with new configurations
- **After customization**: Export after setting up your ideal workflow
- **Regular schedule**: Set a reminder to backup monthly or weekly
- **Multiple versions**: Keep several backup versions in case you need to go back further
- **Test restores**: Periodically test that your backups can be restored successfully

## Configuration Merging

### Import vs Append

Chord Song provides two ways to bring in configurations from files:

1. **Load Config** (Import): **Replaces** your entire configuration
   - Clears all existing mappings and groups
   - Overwrites all settings
   - Use when you want to completely switch to a new configuration

2. **Append Config** (Merge): **Adds to** your existing configuration
   - Keeps all existing mappings and groups
   - Preserves your settings
   - Use when you want to combine configurations

### Replacement Behavior (Load Config)

When you **import** a configuration using **Load Config**:
- **All existing mappings are cleared** and replaced with the imported mappings
- **All existing groups are cleared** and replaced with the imported groups
- **All preferences are overwritten** with the imported values

This means:
- ✅ You get exactly what's in the imported file
- ⚠️ Any mappings or groups you had before are lost (unless you have a backup)

### Merging Behavior (Append Config)

When you **append** a configuration using **Append Config**:
- **All existing mappings are preserved** and new mappings are added
- **Existing groups are preserved** and only new groups (by name) are added
- **Your settings are preserved** (overlay, scripts folder, leader key)

This means:
- ✅ You keep everything you had before
- ✅ New mappings and groups are added
- ✅ Your settings remain unchanged
- ⚠️ Conflicts may occur (duplicate chords, prefix conflicts) - use Conflict Checker to resolve

### Combining Configurations

**Recommended approach**: Use **Append Config** to merge configurations:

1. **Export your current configuration** as a backup (safety first!)
2. **Append the first configuration** you want to merge
3. **Review conflicts** using the automatically-opened Conflict Checker
4. **Resolve any conflicts** (remove duplicates, rename conflicting chords)
5. **Repeat** for additional configurations you want to merge

**Alternative approach**: If you prefer to start fresh:

1. **Export your current configuration** as a backup
2. **Load the first configuration** you want to use
3. **Append additional configurations** one by one
4. **Resolve conflicts** after each append

**Manual approach**: For advanced users:

1. **Export your current configuration** as a backup
2. **Load the first configuration** you want to use
3. **Manually add mappings** from other configurations using the UI
4. **Or edit the JSON files** manually to merge them (requires understanding the format)

### Restoring After Import

If you accidentally import the wrong configuration:

1. **Use Restore Autosave**: If autosave was active, use **Restore Autosave** to get back your previous state
2. **Load your backup**: If you have a manual backup, load it using **Load Config**
3. **Re-import**: If you exported before importing, you can load that export

The autosave file (`.autosave.json`) is **not** overwritten during manual imports, so it can serve as a safety net.
