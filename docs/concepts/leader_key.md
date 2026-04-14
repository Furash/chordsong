The **Leader Key** is the prefix that activates Chord Song's listening mode. Instead of using complex `Ctrl+Alt` combinations, you press a single prefix key (default: `Space`) to begin a chord sequence.

!!! warning "Key Interception"
    When a key is set as the **Leader Key**, you can no longer use it as the first chord. e.g., if you set `Q` you can no longer use it to start a chord like `Q M`. But it can still be used as second or third token in a chord e.g. `M Q`.

!!! tip "Conflict Prevention"
    If you use `Space` as your leader key, make sure to disable Blender's default mapping for Play/Search, or rebind the leader to a less critical key like `/`, `Q`, or `F1`.

## Interaction Model

By default, the leader key supports a multi-tap system:

- **Single Tap**: Opens the overlay and starts listening for a chord (e.g., `Space > M > C`).
- **Double Tap**: Opens the **Recents** list, showing your most frequently used actions.
- **Triple Tap**: Instantly repeats the **Most Recent Action** without opening any menus.

## Navigating the Overlay

Once the overlay is active, you can use the following keys to manage your chord sequence:

| Key | Action |
| :--- | :--- |
| **Backspace** | Deletes the last token and goes back one level in the sequence. |
| **Esc** | Cancels the chord capture and closes the overlay. |

## Customizing Close and Recents Keys

The default close (ESC) and Recents (double-leader) behavior can be customized by creating chord mappings for two special operators:

- **`chordsong.close_overlay`** — Closes the overlay. Mapping the leader key to this operator turns the leader key into a toggle (press to open, press again to close).
- **`chordsong.recents`** — Opens the Recents list. Map to any key (e.g., `r`) for quick access.

When a chord mapping claims the leader key (e.g., `space` → `chordsong.close_overlay`), the default double-tap Recents behavior is replaced by that mapping. ESC always works as a fallback close regardless of custom mappings.

!!! example "Toggle Example"
    Map `space` → `chordsong.close_overlay` and `r` → `chordsong.recents` to get toggle open/close with the leader key and Recents on `r`.

## Setup & Configuration

You can customize the leader key in the add-on preferences

1. Navigate to **Edit > Preferences > Extensions > Chord Song**.
2. Locate the **Leader Key** property.
3. Click the button to capture a new key (good choices: `Space`, `Q`, `/`).

![Leader Key Configuration](/chordsong/scr/leader_key.png)
