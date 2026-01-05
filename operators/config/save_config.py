"""Save config operator."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,attribute-defined-outside-init,invalid-name

import json
import os

import bpy  # type: ignore
from bpy_extras.io_utils import ExportHelper  # type: ignore
from bpy.props import StringProperty  # type: ignore

from ...core.config_io import dump_prefs
from ..common import prefs

class CHORDSONG_OT_Save_Config(bpy.types.Operator, ExportHelper):
    """Save chord mappings to a JSON config file."""

    bl_idname = "chordsong.save_config"
    bl_label = "Save User Config"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        """Show file browser or save directly if config path is set."""
        p = prefs(context)
        config_path = getattr(p, "config_path", "") or ""
        if config_path:
            self.filepath = config_path
            return self.execute(context)

        # Default to extension-specific user directory
        try:
            # Use extension_path_user for extension-specific user directory
            extension_dir = bpy.utils.extension_path_user(__package__, path="", create=True)
            if extension_dir:
                self.filepath = os.path.join(extension_dir, "chordsong.json")
            else:
                self.filepath = os.path.join(os.path.expanduser("~"), "chordsong.json")
        except Exception:
            # Fallback to user_resource if extension_path_user is not available
            try:
                presets_dir = bpy.utils.user_resource("SCRIPTS", path="presets", create=True)
                if presets_dir:
                    folder = os.path.join(presets_dir, "chordsong")
                    os.makedirs(folder, exist_ok=True)
                    self.filepath = os.path.join(folder, "chordsong.json")
                else:
                    self.filepath = os.path.join(os.path.expanduser("~"), "chordsong.json")
            except Exception:
                self.filepath = os.path.join(os.path.expanduser("~"), "chordsong.json")
        return super().invoke(context, event)

    def execute(self, context: bpy.types.Context):
        """Save config to file."""
        p = prefs(context)
        try:
            data = dump_prefs(p)
            text = json.dumps(data, indent=4, ensure_ascii=False)
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(text)
                f.write("\n")
            p.config_path = self.filepath
            self.report({"INFO"}, "Chord Song config saved")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to save config: {ex}")
            return {"CANCELLED"}
