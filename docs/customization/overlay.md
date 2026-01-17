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

<!-- markdownlint-disable MD033 -->
<video autoplay loop muted playsinline>
  <source src="/chordsong/scr/panels_auto_hide.mp4" type="video/mp4">
</video>
<!-- markdownlint-enable MD033 -->

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

Choose the display style:

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/display_style_default.png" alt="Default">
<img src="/chordsong/scr/display_style_custom.png" alt="Custom">
<!-- markdownlint-enable MD033 -->

- **Default**: Simple count display (`a → +5 keymaps`)
- **Custom**: Custom format strings using tokens.

### Custom Format Strings

When **Custom** style is selected, you can define your own format strings using a token system:

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/format_strings.png" alt="Custom Format Strings">
<!-- markdownlint-enable MD033 -->

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

- **Folder Format**: Controls how folders (prefixes with multiple mappings) are displayed
- **Item Format**: Controls how individual chord items are displayed

**Example Custom Formats:**

- Folder: `C n s g` → *Chord* *Count* *Separator_B* *First Group's Label*

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/custom_folder_string.png" alt="Folder Format" width="150">
<!-- markdownlint-enable MD033 -->

- Item: `C I S L T` → *Chord* *Icon* *separator_A* *Label* *Toggle*

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/custom_item_string.png" alt="Item Format" width="250">
<!-- markdownlint-enable MD033 -->

### Theme Management

#### Built-in Presets

- **Reset to Default**: Restores ChordSong's default color scheme

#### Extract from Blender Theme

The **Match Current Blender Theme** button automatically extracts colors from your current Blender theme and applies them to the overlay. This ensures visual consistency with your Blender interface.

#### Import/Export Themes

- **Export**: Save your current overlay theme colors to a JSON file for backup or sharing
- **Import**: Load theme colors from a previously exported JSON file

## Testing

**Debug Tools** in UI tab:

- **Preview Main**: Main overlay with dummy data.
- **Preview Fading**: Fading overlay (10s duration).

Click again to hide.
