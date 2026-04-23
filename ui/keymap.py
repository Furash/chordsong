"""Leader-key keymap accessors.

Reads/writes the addon's leader keymap item across the 3D View, Node
Editor, and Image editor keymaps, honoring the user keyconfig first so
customizations persist. These functions live in ui/ rather than core/
because they reach into bpy.context.window_manager.keyconfigs — a
Blender UI-layer concern, not pure chord-engine logic.

Kept importable from core/__init__.py as a backward-compatible re-export
so existing `from ..core.engine import get_leader_key_type` code keeps
working; new callers should import from here directly.
"""
from ..core.engine import normalize_token


def get_leader_key_type():
    """Return the current leader key type (e.g., 'SPACE', 'ACCENT_GRAVE').
    Defaults to 'SPACE' if the keymap item can't be resolved."""
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager

        # User keyconfig first (user customizations persist there), then addon.
        for kc in (wm.keyconfigs.user, wm.keyconfigs.addon):
            if not kc:
                continue
            km = kc.keymaps.get("3D View")
            if not km:
                continue
            for kmi in km.keymap_items:
                if kmi.idname == "chordsong.leader":
                    return kmi.type
        return "SPACE"
    except Exception:  # pylint: disable=broad-exception-caught
        return "SPACE"


def get_leader_key_token() -> str:
    """Return the current leader key as a display token (e.g., 'space')."""
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager

        for kc in (wm.keyconfigs.user, wm.keyconfigs.addon):
            if not kc:
                continue
            km = kc.keymaps.get("3D View")
            if not km:
                continue
            for kmi in km.keymap_items:
                if kmi.idname == "chordsong.leader":
                    shift_state = getattr(kmi, "shift", False)
                    token = normalize_token(kmi.type, shift=shift_state)
                    if token:
                        return token
                    if kmi.type:
                        return kmi.type.lower()
                    return "<Leader>"
        return "<Leader>"
    except Exception:  # pylint: disable=broad-exception-caught
        return "<Leader>"


def set_leader_key_in_keymap(key_type: str):
    """Set the leader key type across all registered addon keymaps
    (3D View / Node Editor / Image). Updates both user and addon keyconfigs
    so the change persists across addon disable/enable cycles."""
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager

        keymap_names = ["3D View", "Node Editor", "Image"]
        for kc in (wm.keyconfigs.addon, wm.keyconfigs.user):
            if not kc:
                continue
            for km_name in keymap_names:
                km = kc.keymaps.get(km_name)
                if not km:
                    continue
                for kmi in km.keymap_items:
                    if kmi.idname == "chordsong.leader":
                        kmi.type = key_type
                        break
    except Exception:  # pylint: disable=broad-exception-caught
        pass
