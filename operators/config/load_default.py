# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import os

import bpy  # type: ignore

from ...core.config_io import apply_config, loads_json
from ..common import prefs

def _get_default_config_path():
    """Get the path to the default config file in the ui directory."""
    # Try to import ui module and get its path
    try:
        from ... import ui
        if hasattr(ui, "__file__") and ui.__file__:
            ui_dir = os.path.dirname(ui.__file__)
            return os.path.join(ui_dir, "default_mappings.json")
    except (ImportError, AttributeError):
        pass
    
    # Fallback: try relative to this file (operators/config/load_default.py -> ui/)
    # This file is at: operators/config/load_default.py
    # Need to go up 3 levels to get to addon root, then into ui/
    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(addon_dir, "ui", "default_mappings.json")

class CHORDSONG_OT_Load_Default(bpy.types.Operator):
    bl_idname = "chordsong.load_default"
    bl_label = "Load Default Chord Song Config"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        try:
            p._chordsong_suspend_autosave = True

            # Load default config from JSON file
            default_config_path = _get_default_config_path()
            if not os.path.exists(default_config_path):
                self.report({"ERROR"}, f"Default config file not found: {default_config_path}")
                return {"CANCELLED"}

            with open(default_config_path, "r", encoding="utf-8") as f:
                data = loads_json(f.read())

            # Apply the default config
            warnings = apply_config(p, data)
            for w in warnings[:5]:
                self.report({"WARNING"}, w)

            self.report({"INFO"}, "Loaded default config")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to load default config: {ex}")
            return {"CANCELLED"}
        finally:
            p._chordsong_suspend_autosave = False
