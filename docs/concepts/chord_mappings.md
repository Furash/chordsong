# Chord Mappings

Chord mappings connect key sequences to actions in Blender.

## Overview

A chord mapping consists of:
- **Chord**: A sequence of tokens (e.g., `m c` or `f r a`)
- **Action**: What happens when the chord is executed
- **Context**: Where the mapping is active
- **Label**: Human-readable description shown in the overlay
- **Icon**: Visual identifier (Nerd Font icon)

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

<!-- TODO: Explain token format, modifiers (Ctrl, Alt, Shift), special keys -->

## Creating Mappings

<!-- TODO: Explain the mapping creation process -->

## Mapping Properties

<!-- TODO: Detail all mapping properties (chord, label, icon, group, context, type, etc.) -->

## Token Matching

<!-- TODO: Explain how tokens are matched, modifier handling, side-specific modifiers -->
