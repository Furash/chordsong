# Chord Mappings

Chord mappings connect key sequences to actions in Blender.

## Overview

A chord mapping is composed of the following key elements:

| Component | Description |
| :--- | :--- |
| **Chord** | A sequence of one or more key tokens (e.g., `m c` or `f r a`). |
| **Action** | The specific operation to execute (Operator, Property, Toggle, or Script). |
| **Context** | The Blender editor where the mapping is active (e.g., 3D View, Shader Editor). |
| **Label** | The human-readable name displayed in the overlay. |
| **Icon** | A visual identifier using Nerd Font icons. |
| **Group** | An optional category used to organize items into sections within the overlay. |

## Mapping Types

Chord Song supports several types of mappings:

### Operators
Trigger any Blender operator. You can even pass arguments to the operator.
*Example: `object.shade_smooth()`*

### Properties
Toggle or set values for Blender properties.
*Example: `view_3d.show_wireframe`*

### Python Scripts
Run external or internal Python scripts. This is perfect for complex macros or custom logic.
*Example: Path to a `.py` file.*

### Macros
Chain multiple actions together into a single chord.

## Chord Syntax

Chord Song uses a simple yet powerful syntax for defining key sequences. Each chord is a space-separated list of **tokens**.

### AHK-Style Notation

Tokens can include modifier keys using **AutoHotkey-style symbols**. This makes complex combinations easy to type and read.

| Symbol | Modifier | Description |
| :---: | :--- | :--- |
| `^` | **Ctrl** | Control key |
| `!` | **Alt** | Alt key |
| `+` | **Shift** | Shift key |
| `#` | **Win** | Windows/Cmd key |
| `<` | **Left** | Left-side prefix (e.g., `<^` for LCtrl) |
| `>` | **Right** | Right-side prefix (e.g., `>!` for RAlt) |

**Examples:**
- `^c`: Ctrl + C
- `!+f`: Alt + Shift + F
- `<^s`: Left Ctrl + S
- `space g`: Space then G (two-step chord)

### Numpad Chords

Numpad keys are prefixed with `n` to distinguish them from the main row numbers.

| Token | Key | Token | Key |
| :--- | :--- | :--- | :--- |
| `n0` - `n9` | Numpad 0-9 | `n/` | Numpad / |
| `n*` | Numpad * | `n-` | Numpad - |
| `n+` | Numpad + | `n.` | Numpad . |
| `nenter` | Numpad Enter | | |

## Token Matching

Chord Song is smart about how it matches your key presses:

1.  **Order Independent Modifiers**: `^!a` is the same as `!^a`.
2.  **Side Sensitivity**: If you define a mapping with `^a`, it will match both Left and Right Ctrl. If you specify `<^a`, it will **only** match the Left Ctrl.
3.  **Case Insensitivity**: Key tokens are generally treated as lowercase (e.g., `A` and `a` are both `a`).

## Creating Mappings

Mappings can be created in several ways:
- **Right-Click**: Right-click any button or property in Blender and select "Add Chord Mapping".
- **Info Panel**: Extract actions from Blender's history (Info Editor) to batch-create mappings.
- **Preferences**: Manually add and edit mappings in the Chord Song tab.

## Mapping Properties

- **Chord**: The key sequence (e.g., `g g`).
- **Label**: The name shown in the overlay.
- **Icon**: A font icon (Nerd Fonts) to display next to the label.
- **Group**: Optional category to organize your overlay into sections.
- **Context**: The Blender editor where the mapping is active (3D View, Shader Editor, etc.).
