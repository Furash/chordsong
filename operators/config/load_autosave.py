# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import os

import bpy  # type: ignore

from ...core.autosave import autosave_path
from ...core.config_io import apply_config, loads_json
from ..common import prefs

class CHORDSONG_OT_Load_Autosave(bpy.types.Operator):
    bl_idname = "chordsong.load_autosave"
    bl_label = "Restore Autosave"
    bl_options = {"INTERNAL"}

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        ap = autosave_path(getattr(p, "config_path", "") or "")
        if not ap or not os.path.exists(ap):
            self.report({"WARNING"}, "No autosave file found")
            return {"CANCELLED"}

        try:
            p._chordsong_suspend_autosave = True
            with open(ap, "r", encoding="utf-8") as f:
                data = loads_json(f.read())
            warns = apply_config(p, data)
            for w in warns[:5]:
                self.report({"WARNING"}, w)
            self.report({"INFO"}, "Restored autosave")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to restore autosave: {ex}")
            return {"CANCELLED"}
        finally:
            p._chordsong_suspend_autosave = False
