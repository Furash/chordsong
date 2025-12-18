# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,attribute-defined-outside-init

import os

import bpy  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy.props import StringProperty  # type: ignore

from ...core.config_io import apply_config, loads_json
from ..common import prefs

class CHORDSONG_OT_Load_Config(bpy.types.Operator, ImportHelper):
    bl_idname = "chordsong.load_config"
    bl_label = "Load User Config"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        p = prefs(context)
        config_path = getattr(p, "config_path", "") or ""
        if config_path and os.path.exists(config_path):
            self.filepath = config_path
            return self.execute(context)
        if config_path:
            self.filepath = config_path
        return super().invoke(context, event)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        try:
            p._chordsong_suspend_autosave = True
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = loads_json(f.read())
            warns = apply_config(p, data)
            p.config_path = self.filepath
            for w in warns[:5]:
                self.report({"WARNING"}, w)
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to load config: {ex}")
            return {"CANCELLED"}
        finally:
            p._chordsong_suspend_autosave = False
