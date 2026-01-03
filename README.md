<div align="center">
  <img src="docs/logo/chordsong_logo.png" alt="Chord Song Logo" width="400">
</div>

# Chord Song

**Vim-like `<Leader>` key implementation for Blender** — Trigger operators, execute scripts, and modify properties using key sequences.

## Why Chords?

Instead of memorizing awkward `Ctrl+Alt+Shift+F5` combinations, use intuitive sequences like `m c` for **M**esh > **C**ube. A single leader key (default: `Space`) opens up dozens of unique combinations with visual feedback.

## Features

- **Leader Key System** — Single-tap to start chords, double-tap for recents, triple-tap to repeat
- **Context Menu Integration** — Right-click any UI element to add mappings instantly
- **Context Awareness** — Mappings filter by active editor (3D View, UV, Shader Editor, etc.)
- **Four Mapping Types** — Operators, Properties, Toggles, and Custom Python Scripts
- **Conflict Detection** — Built-in checker to identify and resolve mapping conflicts
- **Visual Overlay** — Dynamic overlay shows available chords as you type
- **Groups & Organization** — Organize mappings into groups for better overlay structure

## Quick Start

### Prerequisites

Chord Song requires a **Nerd Font** for icon display:

1. Download a [Nerd Font](https://www.nerdfonts.com/font-downloads) (e.g., Ubuntu Nerd Font)
2. Install it on your system
3. In Blender: **Edit > Preferences > Interface > Text Rendering** → Set **Interface Font** to your Nerd Font

### Installation

1. Download from [GitHub Releases](https://github.com/furash/chordsong/releases) | [Blender Extensions](https://extensions.blender.org/add-ons/chordsong) | [Gumroad](https://furash.gumroad.com/l/chordsong)
2. **Edit > Preferences > Extensions** → **Install from Disk...** → Select `.zip` file
3. Enable "Chord Song" addon

### First Steps

1. **Set Leader Key**: **Preferences > Chord Song** → Configure Leader Key (default: `Space`)
2. **Add Mapping**: Right-click any Blender button → **Add Chord Mapping** → Enter chord (e.g., `m c`)
3. **Use It**: Press Leader Key → Type your chord sequence

**Navigation:**
- `Backspace` — Go back one level
- `Esc` / `Right-Click` — Cancel

## Mapping Types

- **Operator** — Execute Blender operators with parameters
- **Property** — Modify object/material properties
- **Toggle** — Toggle boolean properties on/off
- **Script** — Run custom Python scripts

## Chord Syntax

- `m c` — Simple sequence
- `^c` — Modifiers (`^` = Ctrl, `!` = Alt, `+` = Shift)
- `f1` — Named keys (arrows, function keys, etc.)

See [full documentation](https://furash.github.io/chordsong/concepts/chord/) for complete syntax.

## Requirements

- **Blender** 5.0.0+
- **Nerd Font** (see Prerequisites)

## Documentation

📚 **[Full Documentation →](https://furash.github.io/chordsong/)**

## Security

⚠️ **Python Script Execution**: Chord Song can execute arbitrary Python scripts. Only map chords to scripts you've written or audited.

## License

GPL-3.0-or-later — See [LICENSE](LICENSE)
