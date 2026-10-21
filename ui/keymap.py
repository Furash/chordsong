"""Leader-key keymap accessors.

Reads/writes the addon's leader keymap item across every editor keymap
listed in core.contexts.LEADER_KEYMAPS, honoring the user keyconfig first
so customizations persist. These functions live in ui/ rather than core/
because they reach into bpy.context.window_manager.keyconfigs — a
Blender UI-layer concern, not pure chord-engine logic.

Model: the *default* leader binding lives in a keymap item of its own
(DEFAULT_KEYMAP_NAME), bound to a no-op operator and kept inactive, so it
never fires anywhere; it exists only to be edited by the "Leader Key
(default)" field and copied from. Changing it propagates to every editor
that still follows it. Any editor — the 3D View included — can be given
its own binding from its row (tracked in prefs.leader_key_overrides),
and a context-aware lookup returns the binding of the editor under the
cursor. The default is also recorded in prefs.leader_key_last and
re-applied at register, so it survives even if the keyconfig does not
keep the edit.
Bindings are whole events - Ctrl+Space differs from Space - so compare and
copy them with leader_event / copy_leader_event, never by key type alone.

Kept importable from core/__init__.py as a backward-compatible re-export
so existing `from ..core.engine import get_leader_key_type` code keeps
working; new callers should import from here directly.
"""
from ..core.engine import normalize_token
from ..core.contexts import LEADER_KEYMAPS, LEADER_KEYMAP_NAMES
from ..utils.addon_package import addon_root_package

# The default binding's own keymap and the no-op operator its item binds.
# An EMPTY-space keymap would be active everywhere, so the item is created
# inactive (and the operator passes events through should it ever fire).
DEFAULT_KEYMAP_NAME = "Chord Song Leader Default"
DEFAULT_KEY_IDNAME = "chordsong.leader_default_key"
# Kept under its old name for callers: the "master" binding is the default.
MASTER_KEYMAP_NAME = DEFAULT_KEYMAP_NAME
_LEADER_IDNAMES = frozenset({"chordsong.leader", DEFAULT_KEY_IDNAME})
# The editor keymap used when the space under the cursor is unknown.
_FALLBACK_EDITOR_KEYMAP = LEADER_KEYMAPS[0][0]  # "3D View"

# A leader binding is a whole event, not just a key: the preferences fields
# use full_event=True, so Ctrl+Space and Space are different bindings and
# every comparison/copy below has to cover the modifiers too.
LEADER_EVENT_FIELDS = ("type", "value", "ctrl", "shift", "alt", "oskey")
# The binding the addon registers out of the box, in LEADER_EVENT_FIELDS
# order: a plain Space press. The 3D View row's arrow resets to this.
FACTORY_LEADER_EVENT = ("SPACE", "PRESS", False, False, False, False)
_KEYMAP_BY_SPACE = {space: name for name, space in LEADER_KEYMAPS}


def keymap_name_for_context(context=None) -> str:
    """Leader keymap name for the editor under `context` (the 3D View's
    when the space is unknown or no context is given)."""
    try:
        space = getattr(context, "space_data", None) if context else None
        space_type = getattr(space, "type", None) if space else None
        return _KEYMAP_BY_SPACE.get(space_type or "", _FALLBACK_EDITOR_KEYMAP)
    except Exception:  # pylint: disable=broad-exception-caught
        return _FALLBACK_EDITOR_KEYMAP


def leader_event(kmi):
    """The full binding of a leader keymap item, comparable and hashable.
    None when there is no item."""
    if kmi is None:
        return None
    return tuple(getattr(kmi, f, None) for f in LEADER_EVENT_FIELDS)


def event_signature(kmi) -> str:
    """`leader_event` as a short string, for storing in a prefs field."""
    ev = leader_event(kmi)
    return "|".join(str(v) for v in ev) if ev else ""


def copy_leader_event(dst, src) -> bool:
    """Copy a whole leader binding onto another keymap item."""
    changed = False
    for f in LEADER_EVENT_FIELDS:
        try:
            if getattr(dst, f) != getattr(src, f):
                setattr(dst, f, getattr(src, f))
                changed = True
        except Exception:  # pylint: disable=broad-exception-caught
            continue
    return changed


def apply_event_signature(kmi, signature: str) -> bool:
    """Set a leader keymap item from an `event_signature` string. Returns
    False, changing nothing, when the string does not parse."""
    parts = (signature or "").split("|")
    if len(parts) != len(LEADER_EVENT_FIELDS):
        return False
    values = []
    for f, raw in zip(LEADER_EVENT_FIELDS, parts):
        if f in ("type", "value"):
            if not raw:
                return False
            values.append(raw)
        else:
            values.append(raw == "True")
    changed = False
    for f, v in zip(LEADER_EVENT_FIELDS, values):
        try:
            if getattr(kmi, f) != v:
                setattr(kmi, f, v)
                changed = True
        except Exception:  # pylint: disable=broad-exception-caught
            return False
    return changed


def find_leader_kmi(km_name=MASTER_KEYMAP_NAME, keyconfigs=None):
    """Return (keymap, keymap_item) for the leader binding in `km_name` —
    an editor's leader operator, or the default's no-op item — searching
    the user keyconfig first (customizations live there), then the addon
    keyconfig. (None, None) when not found."""
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager
        if keyconfigs is None:
            keyconfigs = (wm.keyconfigs.user, wm.keyconfigs.addon)
        for kc in keyconfigs:
            if not kc:
                continue
            km = kc.keymaps.get(km_name)
            if not km:
                continue
            for kmi in km.keymap_items:
                if kmi.idname in _LEADER_IDNAMES:
                    return km, kmi
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return None, None


def get_leader_key_type(context=None):
    """Return the leader key type (e.g., 'SPACE', 'ACCENT_GRAVE') bound in
    the editor under `context`, or the master binding without a context.
    Defaults to 'SPACE' if the keymap item can't be resolved."""
    try:
        _, kmi = find_leader_kmi(keymap_name_for_context(context))
        if kmi is None and context is not None:
            _, kmi = find_leader_kmi(MASTER_KEYMAP_NAME)
        return kmi.type if kmi else "SPACE"
    except Exception:  # pylint: disable=broad-exception-caught
        return "SPACE"


def get_leader_key_token(context=None) -> str:
    """Return the leader key as a display token (e.g., 'space') for the
    editor under `context`, or the master binding without a context."""
    try:
        _, kmi = find_leader_kmi(keymap_name_for_context(context))
        if kmi is None and context is not None:
            _, kmi = find_leader_kmi(MASTER_KEYMAP_NAME)
        if kmi is None:
            return "<Leader>"
        shift_state = getattr(kmi, "shift", False)
        token = normalize_token(kmi.type, shift=shift_state)
        if token:
            return token
        if kmi.type:
            return kmi.type.lower()
        return "<Leader>"
    except Exception:  # pylint: disable=broad-exception-caught
        return "<Leader>"


def set_leader_key_in_keymap(key_type: str) -> bool:
    """Set the leader key type on the default and across every editor
    keymap, clearing the modifiers. Used when a loaded config carries a
    plain "leader_key" string; the interactive path goes through
    propagate_master_event, which copies the whole binding. Returns True
    if anything changed."""
    updated = False
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager

        for kc in (wm.keyconfigs.addon, wm.keyconfigs.user):
            if not kc:
                continue
            for km_name in (DEFAULT_KEYMAP_NAME, *LEADER_KEYMAP_NAMES):
                km = kc.keymaps.get(km_name)
                if not km:
                    continue
                for kmi in km.keymap_items:
                    if kmi.idname in _LEADER_IDNAMES:
                        kmi.type = key_type
                        for mod in ("ctrl", "shift", "alt", "oskey"):
                            try:
                                setattr(kmi, mod, False)
                            except Exception:  # pylint: disable=broad-exception-caught
                                pass
                        updated = True
                        break
    except Exception:  # pylint: disable=broad-exception-caught
        pass
    return updated


def leader_overrides(keyconfigs=None):
    """Editors whose leader binding differs from the default, as a list of
    (keymap_name, key_type). Empty when every editor matches. Compares the
    whole event, so Ctrl+Space counts as an override of Space."""
    _, master = find_leader_kmi(MASTER_KEYMAP_NAME, keyconfigs)
    if master is None:
        return []
    master_event = leader_event(master)
    diffs = []
    for km_name in LEADER_KEYMAP_NAMES:
        _, kmi = find_leader_kmi(km_name, keyconfigs)
        if kmi is not None and leader_event(kmi) != master_event:
            diffs.append((km_name, kmi.type))
    return diffs


def propagate_master_event(skip_keymaps=()) -> bool:
    """Copy the default leader binding onto every editor keymap except the
    ones named in `skip_keymaps` (the editors the user gave their own key).
    Writes to both keyconfigs so the change survives a disable/enable."""
    try:
        import bpy  # type: ignore
        wm = bpy.context.window_manager
    except Exception:  # pylint: disable=broad-exception-caught
        return False
    _, master = find_leader_kmi(MASTER_KEYMAP_NAME)
    if master is None:
        return False
    skip = set(skip_keymaps) | {MASTER_KEYMAP_NAME}
    updated = False
    for kc in (wm.keyconfigs.addon, wm.keyconfigs.user):
        if not kc:
            continue
        for km_name in LEADER_KEYMAP_NAMES:
            if km_name in skip:
                continue
            km = kc.keymaps.get(km_name)
            if not km:
                continue
            for kmi in km.keymap_items:
                if kmi.idname == "chordsong.leader":
                    updated = copy_leader_event(kmi, master) or updated
                    break
    return updated


_sync_pending = False


def schedule_master_sync(master_signature: str, propagate: bool = True, skip_keymaps=()):
    """Propagate a changed master leader key to the editor keymaps.

    Called from the preferences draw code, which must not mutate data
    itself, so the write is deferred to a zero-delay bpy.app.timers tick.
    Records the new master signature in prefs.leader_key_last so the next
    draw sees no pending change. With propagate=False only the record is
    updated — used on first draw so pre-existing customizations survive.
    ``skip_keymaps`` names the editors the user gave their own key; they
    keep it.
    """
    global _sync_pending  # pylint: disable=global-statement
    if _sync_pending:
        return
    _sync_pending = True
    package_name = addon_root_package(__package__)

    def _sync():
        global _sync_pending  # pylint: disable=global-statement
        _sync_pending = False
        try:
            import bpy  # type: ignore
            if propagate:
                propagate_master_event(skip_keymaps)
            prefs = bpy.context.preferences.addons[package_name].preferences
            prefs.leader_key_last = master_signature
            from ..utils.redraw import tag_redraw_all_areas
            tag_redraw_all_areas()
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return None

    try:
        import bpy  # type: ignore
        bpy.app.timers.register(_sync, first_interval=0.0)
    except Exception:  # pylint: disable=broad-exception-caught
        _sync_pending = False
