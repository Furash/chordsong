# Chord Mappings

Every chord mapping consists of the following properties:

- **Chord**: The key sequence (e.g., `g g`).
- **Label**: The name shown in the overlay.
- **Icon**: A font icon (Nerd Fonts) to display next to the label. Can be any symbol supported by the font.
- **Group**: Optional category to organize your overlay into sections.
- **Context**: The Blender editor where the mapping is active (3D View, Shader Editor, etc.).

## Adding Mappings

There are several ways to add chord mappings:

- **Preferences**: Manually add and edit mappings in the Chord Song preferences tab.
- **Context Menu**: Right-click any button or menu item in Blender and select **Add Chord Mapping**.
- **Info Panel**: Select operator history rows in Blender's Info Editor, right-click, and select **Extract to Chord Mapping** for batch creation.
- **Copy & Paste**: Copy and paste chord snippets from clipboard (see [Copy & Paste Sharing](chord_serialization.md)).
- **Import/Append**: Load or merge configurations from JSON files (see [Import & Export](import_export.md)).
- **Manual Editing**: Advanced users can edit the JSON configuration file directly. See [Configuration File Format](import_export.md#configuration-file-format) for details.

## Context-Specific Organization

The Mappings tab organizes chords by **Context** with one row per editor, laid out in two columns. A row is the editor button, then the editor's modes as icon buttons with their chord counts, then that editor's leader key. Hover an icon for the mode's name. Clicking the editor button selects its first mode; clicking an icon selects that mode. The 3D View's eight Edit modes get a row of their own, **Edit Modes**, right under the 3D View. The first entry, **Global**, holds the chords that are active in every editor. They are managed only there: an editor's tab lists that editor's own mappings and shows an "Also active here" link for Global and for the parent contexts it inherits from. The contexts are:

- **3D View**: Object, Sculpt, Paint and Pose mode, plus one context per Edit mode (mesh, curve, armature, text, lattice, metaball, grease pencil, point cloud)
- **Geometry Nodes**, **Shader Editor**, **Compositor**: Node editors, by tree type
- **UV Editor**: UV / Image Editor, with its Paint mode
- **Video Sequencer**: timeline, with its Preview
- **Movie Clip**: Tracking (Clip view), Graph view, Dope Sheet view and Mask mode
- **Dope Sheet**, **Graph Editor**, **NLA Editor**: Animation editors

See [Contexts](../concepts/contexts.md) for the full list. Selecting a context also sets the context used by **Add New Chord**.

Each mapping row has a **Contexts** button (globe icon) that opens one dialog showing every context as a toggle. Contexts where an identical copy of the chord already exists are pre-ticked, so the dialog shows where the chord is active right now:

- **Tick** a context to create a copy of the chord there.
- **Untick** a context to remove that copy.
- **Make Global** replaces every copy with one Global mapping, active in every editor.

The row you opened the dialog from is kept, re-contexted if you unticked its own context, so its place in the list survives. Setting a mapping's **Context** dropdown does a plain relabel of that one mapping only; use the dialog when copies are involved.

Context tabs turn red when a chord in that context is in conflict. A conflict between a Global chord and an editor chord marks both tabs, and each tab lists the other party greyed out next to the chord it clashes with. While a search is active, editor tabs also list matching Global chords greyed out, so a search finds every chord active in that editor.

## Leader Key

The **Leader Key (default)** field at the top of the Mappings tab is the key every editor follows until it is given one of its own. Each editor's row, the 3D View's included, ends with its own key (the key icon, then the field): the field shows the key in use, greyed while it is the default. To give that editor a different key, for example when ++space++ should keep driving playback in the Video Sequencer, press the **Override** icon next to the field and then press the new key. The arrow icon that replaces it resets the editor to the default key. A note under the default field says how many editors use their own key. Changing the default key moves the editors that still followed it; editors with their own key keep it.

## Search Functionality

The search box at the top of the Mappings tab provides advanced filtering across:

- **Chords**: Search by key sequence (e.g., "g g")
- **Labels**: Search by action description (e.g., "frame selected")
- **Operators**: Search by operator ID (e.g., "view3d.view_selected")
- **Properties**: Search by property path or value
- **Toggles**: Search by toggle path
- **Scripts**: Search by script file path

Search is case-insensitive and filters mappings in real-time. Use the **X** button to clear the search.

### Search Filters

You can use prefix filters to search within specific fields:

- **`c:`** - Search only in chords (e.g., `c: g` finds all chords starting with "g")
- **`l:`** - Search only in labels (e.g., `l: frame` finds all labels containing "frame")
- **`o:`** - Search only in operators (e.g., `o: view3d` finds all operators containing "view3d")
- **`p:`** - Search only in properties (e.g., `p: space_data` finds all property mappings with "space_data")
- **`t:`** - Search only in toggles (e.g., `t: overlay` finds all toggle mappings with "overlay")
- **`s:`** - Search only in scripts (e.g., `s: node` finds all script mappings with "node" in the filename)

When using a filter, groups and individual mappings containing matching results are automatically expanded for easy visibility.

The same prefix syntax works in the [Chord Search overlay](../features/search.md), so one set of habits covers both.

## Collapsible Items

- **Fold All**: Collapse all groups to show headers only
- **Unfold All**: Expand all groups to show all mappings
- **Individual Groups**: Click the triangle icon next to each group name to expand/collapse

## Sharing and Backup

- **[Copy & Paste](chord_serialization.md)**: Share chord snippets with others or backup specific chords to clipboard
- **[Import & Export](import_export.md)**: Save and load entire configurations or groups of chords

## Mapping Types

Each chord mapping type has its own set of attributes and configuration options.

Mapping type can be switched by clicking one of the icons in the mapping item.

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/mapping_types.png" alt="Mapping Type Selector" width="200">
<!-- markdownlint-enable MD033 -->

- [Operator Mapping](mappings/operator.md)
- [Property Mapping](mappings/property.md)
- [Toggle Mapping](mappings/toggle.md)
- [Script Mapping](mappings/script.md)
