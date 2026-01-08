"""Helpers for dealing with legacy vs Extension package namespaces.

Blender Extensions are installed under a namespace like:
  bl_ext.{repository_module_name}.{addon_id}[.{subpackages...}]

Legacy add-ons typically use:
  {addon_id}[.{subpackages...}]
"""


def addon_root_package(package: str | None) -> str:
    """Return the add-on root package used for preferences/extension storage.

    Examples:
    - "bl_ext.user_default.chordsong.ui" -> "bl_ext.user_default.chordsong"
    - "chordsong.ui" -> "chordsong"
    """
    if not package:
        return ""

    parts = package.split(".")
    if parts and parts[0] == "bl_ext":
        # Extensions: bl_ext.{repo}.{addon_id}[...]
        if len(parts) >= 3:
            return ".".join(parts[:3])
        return package

    # Legacy add-ons: {addon_id}[...]
    return parts[0]
