A chord is a sequence of one or more key tokens (e.g., `m c` or `f r a`).

| Component | Description |
| :--- | :--- |
| **Chord** | A sequence of one or more key tokens (e.g., `m c` or `f r a`). |
| **Action** | The specific operation to execute (Operator, Property, Toggle, or Script). |
| **Context** | The Blender editor where the mapping is active (e.g., 3D View, Shader Editor). |
| **Label** | The chord's name displayed in the overlay. |
| **Icon** | A visual identifier using Nerd Font icons or any other symbol. |
| **Group** | An optional category used to organize items into sections within the overlay. |

## Chord Syntax

Chord Song uses a simple syntax for defining key sequences. 
Each chord is a space-separated list of **tokens**. The sequence always begins after you press the [Leader Key](leader_key.md), which intercepts all subsequent input.

!!! note "Input Interception"
    The Leader Key will effectively "steal" all subsequent input for any other chord. It means that if you assign `q` as a Leader Key, you can no longer use `q` to start any other chord combinations. But you can still use `q` as a second or third chord token in a chord, e.g., `m q` but not `q m`.

### AHK-Style Notation

Tokens can include modifier keys using **AutoHotkey-style symbols**. This makes complex combinations easy to type and read.

| Symbol | Modifier | Description |
| :---: | :--- | :--- |
| `^` | **Ctrl** | Control key |
| `!` | **Alt** | Alt key |
| `+` | **Shift** | Shift key |
| `#` | **Win** | Windows/Cmd key |
| `>` | **Right** | Right-side prefix (e.g., `>!` for RAlt, `>+` for RShift) |

**Examples:**

| Chord | Combination | Description |
| :--- | :--- | :--- |
| `^c` | Ctrl + C | Standard control modifier. |
| `!+f` | Alt + Shift + F | Multiple modifiers combined. |
| `<^s` | Left Ctrl + S | Explicit side sensitivity (Left side). |

### Named Keys

For special keys that aren't letters or numbers, use these aliases:

| Token | Key |
| :--- | :--- |
| `tab` | Tab key |
| `space` | Spacebar |
| `enter` | Enter / Return |
| `esc` | Escape |
| `grave` | Grave (`` ` ``) / Tilde key |
| `up`, `down`, `left`, `right`| Arrow keys |
| `home`, `end`, `insert`, `delete` | Navigation keys |
| `pageup`, `pagedown` | Page scrolling keys |
| `f1` - `f12` | Function keys |

Punctuation keys like `,`, `.`, `/`, `;`, `'`, `[`, `]`, `\`, `-`, `=` are used directly as tokens.

### Numpad Chords

Numpad keys are prefixed with `n` to distinguish them from the main row numbers.

| Token | Key | Token | Key |
| :--- | :--- | :--- | :--- |
| `n0` - `n9` | Numpad 0-9 | `n/` | Numpad / |
| `n*` | Numpad * | `n-` | Numpad - |
| `n+` | Numpad + | `n.` | Numpad . |
| `nenter` | Numpad Enter | | |

!!! note "Token Matching"
    **Order Independent Modifiers**: `^!a` is the same as `!^a`.

    **Side Sensitivity**: If you define a mapping with `^a`, it will match both Left and Right `Ctrl`. If you specify `>^a`, it will **only** match the `Right Ctrl`.

    **Case Sensitivity**: Uppercase characters are treated as having an implicit `Shift` modifier (e.g., `C` is shorthand for `+c`), while lowercase characters (e.g., `c`) represent the key without Shift. This means `c` and `C` can be used for different mappings.


