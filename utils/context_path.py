"""Path normalization utilities for property and context paths.

Also hosts small disk-path validators (e.g. is_script_path_allowed) that
need to stay bpy-free so they can be unit-tested without a Blender runtime.
"""
import os
import re


def is_script_path_allowed(filepath, scripts_folder):
    """Return (allowed, reason) for executing `filepath` under `scripts_folder`.

    If `scripts_folder` is empty/None, confinement is off (legacy behavior —
    a user who never configured a folder keeps working). Otherwise `filepath`
    must resolve (via realpath) to a location under `scripts_folder`, also
    real-resolved. Normalizes case for Windows/HFS+ compatibility.

    Returns (True, "") when allowed, (False, reason) when blocked.
    """
    if not scripts_folder:
        return True, ""
    if not filepath:
        return False, "Empty script path."
    try:
        folder_real = os.path.realpath(scripts_folder)
        file_real = os.path.realpath(filepath)
        folder_norm = os.path.normcase(folder_real)
        file_norm = os.path.normcase(file_real)
        common = os.path.commonpath([folder_norm, file_norm])
    except (ValueError, OSError):
        # commonpath raises ValueError for mixed drives on Windows — treat
        # as "not under the folder" and reject.
        return False, (
            f"Script {filepath!r} cannot be resolved against scripts folder "
            f"{scripts_folder!r}."
        )
    if common != folder_norm:
        return False, (
            f"Script {filepath!r} is outside the configured scripts folder "
            f"({scripts_folder!r}). Move it inside or update Preferences."
        )
    return True, ""


def normalize_bpy_data_path(path):
    """Normalize bpy.data paths to context-relative paths.

    Converts patterns like scenes["Scene"] -> scene, worlds["World"] -> world, etc.
    Removes bpy.data. prefix and indexed collection access, converting plural to singular.
    Special handling for screens[...].areas[...].spaces[...] -> space_data

    Args:
        path: Property path string (may include bpy.data. prefix)

    Returns:
        Normalized path string

    Examples:
        >>> normalize_bpy_data_path('bpy.data.scenes["Scene"].ADDON.toggleSomething')
        'scene.ADDON.toggleSomething'
        >>> normalize_bpy_data_path('scenes["Scene"].ADDON.something')
        'scene.ADDON.something'
        >>> normalize_bpy_data_path('bpy.data.worlds["World"].use_nodes')
        'world.use_nodes'
        >>> normalize_bpy_data_path('bpy.data.screens["Modeling"].areas[1].spaces[0].overlay.show_face_orientation')
        'space_data.overlay.show_face_orientation'
    """
    cleaned_path = path

    # Remove bpy.data. prefix if present
    if cleaned_path.startswith("bpy.data."):
        cleaned_path = cleaned_path[len("bpy.data."):]

    # Remove bpy.context. prefix — copy_data_path_button(full_path=True) emits
    # it for non-ID roots such as preferences.addons["..."].preferences.flag.
    # The executor already walks from bpy.context, so the prefix is redundant.
    if cleaned_path.startswith("bpy.context."):
        cleaned_path = cleaned_path[len("bpy.context."):]

    # Special case: screens[...].areas[...].spaces[...] -> space_data
    # Pattern: screens["name"].areas[N].spaces[M].rest_of_path -> space_data.rest_of_path
    screens_match = re.match(r'^screens\[[^\]]+\]\.areas\[\d+\]\.spaces\[\d+\]\.(.+)$', cleaned_path)
    if screens_match:
        rest_of_path = screens_match.group(1)
        return f'space_data.{rest_of_path}'

    # Remove indexed collection access and convert to singular
    # Pattern: collection_name["index"].rest_of_path -> singular.rest_of_path
    # This works whether or not the path had bpy.data. prefix
    match = re.match(r'^(\w+)\[[^\]]+\]\.(.+)$', cleaned_path)
    if match:
        collection_name = match.group(1)
        rest_of_path = match.group(2)
        # Convert plural to singular: remove trailing 's'
        singular = collection_name[:-1] if collection_name.endswith('s') else collection_name
        cleaned_path = f'{singular}.{rest_of_path}'

    return cleaned_path


_KEY_SEGMENT_RE = re.compile(r"""\[\s*(?:"([^"]*)"|'([^']*)'|(-?\d+))\s*\]""")


def split_context_path(path):
    """Tokenize a context path into attribute names and bracket segments.

    Returns a list where plain attribute names are ``str`` and bracket
    accesses are tuples: ``("key", "name")`` for quoted string keys and
    ``("index", 3)`` for integer indices.

    >>> split_context_path('preferences.addons["bl_ext.a.B"].preferences.flag')
    ['preferences', 'addons', ('key', 'bl_ext.a.B'), 'preferences', 'flag']

    Raises ``ValueError`` on malformed input (unterminated bracket, unquoted
    non-integer key, empty attribute name).
    """
    segments = []
    i = 0
    n = len(path)
    name = ""
    while i < n:
        ch = path[i]
        if ch == ".":
            if name:
                segments.append(name)
                name = ""
            elif not segments or isinstance(segments[-1], str):
                raise ValueError(f'Empty attribute name in path "{path}"')
            i += 1
        elif ch == "[":
            if name:
                segments.append(name)
                name = ""
            m = _KEY_SEGMENT_RE.match(path, i)
            if not m:
                raise ValueError(f'Malformed bracket access in path "{path}" at offset {i}')
            if m.group(3) is not None:
                segments.append(("index", int(m.group(3))))
            else:
                key = m.group(1) if m.group(1) is not None else m.group(2)
                segments.append(("key", key))
            i = m.end()
        else:
            name += ch
            i += 1
    if name:
        segments.append(name)
    return segments


def _segment_text(seg):
    if isinstance(seg, str):
        return seg
    kind, val = seg
    return f'["{val}"]' if kind == "key" else f"[{val}]"


def _join_segments(segments):
    out = ""
    for seg in segments:
        text = _segment_text(seg)
        if isinstance(seg, str) and out:
            out += "."
        out += text
    return out


def resolve_context_path(root, path):
    """Walk ``path`` from ``root`` down to the owner of the final property.

    Returns ``(owner, prop_name, None)`` on success or ``(None, None, error)``
    on failure, where ``error`` is a human-readable message naming the segment
    that could not be resolved. The final segment must be a plain attribute
    name — that is the property callers will get/set on ``owner``.

    Attribute segments use ``getattr``; bracket segments use ``obj[key]`` /
    ``obj[index]`` (bpy_prop_collection semantics).
    """
    try:
        segments = split_context_path(path)
    except ValueError as ex:
        return None, None, str(ex)

    if len(segments) < 2:
        return None, None, (
            f'Invalid context path "{path}" — must include context '
            f'(e.g. "space_data.overlay.show_stats")'
        )
    prop_name = segments[-1]
    if not isinstance(prop_name, str):
        return None, None, (
            f'Invalid context path "{path}" — must end with a property name, '
            f'not a bracket access'
        )

    obj = root
    walked = []
    for seg in segments[:-1]:
        walked.append(seg)
        if isinstance(seg, str):
            nxt = getattr(obj, seg, None)
            if nxt is None:
                return None, None, (
                    f'Path "{path}": attribute "{_join_segments(walked)}" does not exist on context'
                )
        else:
            kind, val = seg
            try:
                nxt = obj[val]
            except (KeyError, IndexError, TypeError):
                nxt = None
            if nxt is None:
                return None, None, (
                    f'Path "{path}": no item {_segment_text(seg)} in "{_join_segments(walked[:-1])}"'
                )
        obj = nxt

    if not hasattr(obj, prop_name):
        parent = _join_segments(segments[:-1]) or "context"
        return None, None, f'Path "{path}": "{parent}" has no attribute "{prop_name}"'
    return obj, prop_name, None


def _is_addon_preferences(pointer):
    rna = getattr(pointer, "rna_type", None)
    while rna is not None:
        if getattr(rna, "identifier", None) == "AddonPreferences":
            return True
        rna = getattr(rna, "base", None)
    return False


def _same_struct(a, b):
    if a is b:
        return True
    try:
        return a.as_pointer() == b.as_pointer()
    except AttributeError:
        return False


def addon_prefs_context_path(button_pointer, prop_name, addons):
    """Build ``preferences.addons["<module>"].preferences.<prop_name>`` for a
    right-clicked AddonPreferences property.

    ``addons`` is an iterable of objects with ``module`` and ``preferences``
    (``bpy.context.preferences.addons``). Blender does not expose a reliable
    ``bl_idname`` on AddonPreferences *instances*, so the addon key is found
    by matching the pointer against each addon's ``preferences`` struct.

    Returns ``None`` when ``button_pointer`` is not an AddonPreferences or no
    enabled addon owns it.
    """
    if button_pointer is None or not _is_addon_preferences(button_pointer):
        return None
    for addon in addons:
        prefs = getattr(addon, "preferences", None)
        if prefs is None:
            continue
        if _same_struct(prefs, button_pointer):
            return f'preferences.addons["{addon.module}"].preferences.{prop_name}'
    return None


_OPERATOR_IDNAME_RE = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")


def is_operator_idname(text):
    """True if ``text`` is shaped like an operator bl_idname (``module.name``).

    Panels/menus/AddonPreferences also carry ``bl_idname`` — the latter even
    reads back as garbage bytes on instances — so the attribute alone can't
    identify an operator.
    """
    return isinstance(text, str) and bool(_OPERATOR_IDNAME_RE.match(text))
