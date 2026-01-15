# Overlay Configuration

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/prefs_ui.png" alt="UI Settings">
<!-- markdownlint-enable MD033 -->

## Display Control

- **Hide T & N Panels During Leader**: Automatically hide Tool (T) and Properties (N) panels while the Leader key modal is active. Panels are restored when the modal finishes.
- **Global Overlay Visibility**: Toggle main overlay.
- **Enable Fading Overlay**: Show confirmation after executing a chord.
- **Show Header**: Toggle header.
- **Show Footer**: Toggle footer.

### Panel Hiding

Automatically hides Tool (T) and Properties (N) panels in the active editor (3D Viewport, Node Editor, UV/Image Editor) while any overlay modal is running. Panels are restored to their original state when the modal closes.

## Layout & Items

- **Max Items**: Items per column.
- **Column Layout**: Rows before wrapping.
- **Vertical Gap**: Item spacing.
- **Line Height**: Text line height multiplier.
- **Horizontal Column Gap**: Column spacing.

## Typography

Enhanced typography controls with separate font sizes for all overlay elements:

- **Header Size**: Font size for overlay header text
- **Chord Size**: Font size for chord sequence text
- **Body Size**: Font size for labels and descriptions
- **Footer Size**: Font size for footer text
- **Fading Font Size**: Font size for the confirmation overlay
- **Toggle Icon Size**: Size of toggle state icons
- **Toggle Vertical Offset**: Vertical positioning offset for toggle icons

## Positioning

Controls overlay position.

- **Anchor Position**: Corner or edge anchor.
- **X Offset**, **Y Offset**: Offset from anchor.

## Appearance

### Overlay Style Presets

Choose one of the 4 preset styles:

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/overlay_style_a.png" alt="Default">
<img src="/chordsong/scr/overlay_style_b.png" alt="Groups After">
<img src="/chordsong/scr/overlay_style_c.png" alt="Groups First ::">
<img src="/chordsong/scr/overlay_style_d.png" alt="Groups First ->">
<!-- markdownlint-enable MD033 -->

- **Default**: Simple count display (`a → +5 keymaps`)
- **Groups After**: Count first, then groups (`a → +5 keymaps :: Modeling`)
- **Groups First**: Groups first, then count (`a → Modeling → 5 keymaps`)
- **Hybrid**: Minimal with groups and compact count (`a → Modeling :: +5`)

### Custom Format Strings

When **Custom** style is selected, you can define your own format strings using a token system:

**Available Tokens:**

- `C` = Chord
- `I` = Icon (mapping's icon)
- `i` = Group Icon (first group's icon)
- `G` = All Groups
- `g` = First Group Only
- `L` = Label
- `N` = Verbose Count (e.g., "+5 keymaps")
- `n` = Compact Count (e.g., "+5")
- `S` = Separator A (default: `→`)
- `s` = Separator B (default: `::`)

**Format Strings:**

- **Folder Format**: Controls how folders (prefixes with multiple mappings) are displayed
- **Item Format**: Controls how individual chord items are displayed

**Example Custom Formats:**

- Folder: `C S G s n` → `a → Modeling :: +5`
- Folder with group icon: `C i S G s n` → `a  Modeling :: +5` (shows group icon before group name)
- Item: `C I L` → `a  Save`
- Item with group icon: `C i I L` → `a   Save` (shows both group icon and mapping icon)

### Theme Management

#### Built-in Presets

- **Reset to Default**: Restores ChordSong's default color scheme

#### Extract from Blender Theme

The **Match Current Blender Theme** button automatically extracts colors from your current Blender theme and applies them to the overlay. This ensures visual consistency with your Blender interface.

#### Import/Export Themes

- **Export**: Save your current overlay theme colors to a JSON file for backup or sharing
- **Import**: Load theme colors from a previously exported JSON file

Theme files include all color settings:

- Chord, Label, Icon, Group, Counter colors
- Toggle states (ON/OFF)
- Header, Footer, Recents key colors
- Separators and background colors

### Colors & Opacity

Full control over per-element colors and opacity:

- **Chord Color**: Color of the chord sequence text
- **Label Color**: Color of the action description
- **Icon Color**: Color of Nerd Font icons
- **Group Color**: Color of group names in overlay
- **Counter Color**: Color of item count text
- **Toggle ON/OFF**: Colors for toggle state indicators
- **Header Text**: Color of overlay header text
- **Recents Key**: Color of recent actions hotkey indicator
- **Separators**: Color and opacity of separator lines
- **Backgrounds**: Colors for list, header, and footer backgrounds (with opacity control)

## Testing

**Debug Tools** in UI tab:

- **Preview Main**: Main overlay with dummy data.
- **Preview Fading**: Fading overlay (10s duration).

Click again to hide.
