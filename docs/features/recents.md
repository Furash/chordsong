# Recents System

Double-tap the leader key to open the Recents menu. Execute items by pressing number or letter keys.

Triple-tap the leader key to repeat the most recent action.

![Recents](/chordsong/scr/recents.png){ width="640" }

## Custom Recents Key

You can assign a custom key to open Recents by creating a chord mapping with the operator `chordsong.recents`. For example, mapping `r` → `chordsong.recents` opens the Recents list when you press `r` during chord capture.

The default double-leader behavior continues to work alongside any custom mapping. If the leader key is remapped to another operator (e.g., `chordsong.close_overlay`), the double-leader fallback is replaced and you'll need a custom Recents mapping to access Recents.
