"""Panel visibility helpers for overlay operators."""


def restore_panel_attr(space, panel_state, key, attr):
    """Restore a single panel attribute on `space` from `panel_state[key]`.

    No-op if the key is absent, the attribute doesn't exist on the space,
    or the current value already matches.
    """
    if key not in panel_state:
        return
    if not hasattr(space, attr):
        return
    target = panel_state[key]
    if getattr(space, attr) != target:
        setattr(space, attr, target)
