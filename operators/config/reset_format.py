"""Reset overlay format string operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,relative-beyond-top-level

import bpy
from ..common import prefs

_TARGET_PROPS = {
    "FOLDER": "overlay_format_folder",
    "ITEM": "overlay_format_item",
}

def _default_recipe(p, target: str) -> str:
    prop_name = _TARGET_PROPS.get(target, "overlay_format_folder")
    return p.bl_rna.properties[prop_name].default

class CHORDSONG_OT_Reset_Format(bpy.types.Operator):
    bl_idname = "chordsong.reset_format"
    bl_label = "Reset Format to Default"
    bl_options = {"INTERNAL"}

    target: bpy.props.EnumProperty(
        items=(
            ("FOLDER", "Folder Format", ""),
            ("ITEM", "Item Format", ""),
        ),
        default="FOLDER",
    )

    @classmethod
    def description(cls, context, properties):
        p = prefs(context)
        recipe = _default_recipe(p, properties.target)
        return f"Reset to the default recipe: {recipe}"

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        prop_name = _TARGET_PROPS[self.target]
        setattr(p, prop_name, _default_recipe(p, self.target))
        return {"FINISHED"}
