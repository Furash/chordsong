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
