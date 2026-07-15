# Chord Search

The Search Overlay lets you find and run any chord by typing part of its label — useful when your library has grown past what you can memorize. Each result also shows the real chord sequence, so searching doubles as a way to (re)learn your chords.

![Chord Search Overlay](/chordsong/scr/chord_search_overlay.png){ width="640" }

## Quick Access

The operator is `chordsong.search`. Map it to a chord of your choice (for example `<Leader> /`) by adding an **Operator** mapping with `chordsong.search` as the operator ID. Invoking it again while the overlay is open closes it (toggle).

## Features

### Fuzzy Search

Type letters to filter chords in real-time. Plain queries fuzzy-match against the mapping **label** and **group**, sorted by relevance. Only chords available in the current editor context are shown — the same context filtering the leader overlay uses.

### Search Filters

The same prefix syntax as the [Chord Search field](../configuration/mappings.md#search-filters) in Preferences works here:

- **`c:`** - Search only in chords (e.g., `c:g g`)
- **`l:`** - Search only in labels (e.g., `l:frame`)
- **`o:`** - Search only in operators (e.g., `o:view3d.view_selected`)
- **`p:`** - Search only in properties (path or value)
- **`t:`** - Search only in toggles
- **`s:`** - Search only in scripts

Prefixed queries use exact substring matching within the chosen field (identical behavior to the Preferences search) and keep your mapping order. A bare prefix like `t:` lists everything of that type.

### Learn the Real Chord

Every result displays its actual chord sequence after the label:

```
1  Select All   :: s a
2  Set Frame    :: s f
```

Press the digit to run it now — or remember the chord and use it directly next time.

### Numbered Execution

The first 9 results are assigned numbers **1-9**:

- Press **1-9** to execute the corresponding chord
- Results beyond the first 9 are display-only until filtering brings them into the top 9
- Hold **Ctrl/Alt/Shift** with a digit to type the digit into the query instead

### Mouse Support

- **Hover** highlights the row under the cursor
- **Click** runs the chord and closes the overlay
- **Ctrl+Click** runs the chord and keeps the overlay open for chaining

### Execution

All mapping types work — operators (including operator chains), toggles, properties, and scripts. Successful runs show the usual fading confirmation and are added to your [Recents](recents.md) list. Script mappings still require **Allow Custom User Scripts** to be enabled.

## Keyboard Shortcuts

| Key | Action |
| :--- | :--- |
| **1-9** | Execute result at that position |
| **A-Z**, **Space** | Add character to the query |
| **`;` / `.` / `-`** | Type `:` `.` `-` (Shift+`-` for `_`) for filter syntax |
| **Ctrl/Alt/Shift + Number** | Add number to the query |
| **Backspace** | Remove last query character (closes when empty) |
| **ESC / Right-Click** | Close overlay |

## Customization

The Search Overlay reuses the [Scripts Overlay layout settings](scripts_overlay.md#customization) (max items, rows per column, gaps, label truncation) from the **UI** tab of Preferences.
