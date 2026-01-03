# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,attribute-defined-outside-init

import os

import bpy  # type: ignore
from bpy_extras.io_utils import ImportHelper  # type: ignore
from bpy.props import StringProperty  # type: ignore

from ...core.config_io import apply_config_append, loads_json, CHORDSONG_CONFIG_VERSION
from ..common import prefs

def _validate_chordsong_config(data: dict) -> tuple[bool, str]:
    """
    Validate that the data looks like a valid Chordsong config file.
    Returns (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Config root must be a JSON object"
    
    # Check for expected Chordsong config keys
    expected_keys = {"mappings", "groups", "overlay"}
    has_expected_key = any(key in data for key in expected_keys)
    
    if not has_expected_key:
        return False, "File does not appear to be a Chordsong config (missing mappings, groups, or overlay)"
    
    # Check version if present
    version = data.get("version")
    if version is not None and version not in (None, 1):
        return False, f"Unsupported config version: {version} (current {CHORDSONG_CONFIG_VERSION})"
    
    # Validate mappings structure if present
    if "mappings" in data:
        mappings = data["mappings"]
        if not isinstance(mappings, list):
            return False, "Mappings must be a list"
        # Check at least one mapping has expected structure
        if mappings:
            first_mapping = mappings[0]
            if not isinstance(first_mapping, dict):
                return False, "Each mapping must be an object"
            # Check for required fields
            if "chord" not in first_mapping:
                return False, "Mappings must contain 'chord' field"
            if "mapping_type" not in first_mapping:
                return False, "Mappings must contain 'mapping_type' field"
    
    # Validate groups structure if present
    if "groups" in data:
        groups = data["groups"]
        if not isinstance(groups, list):
            return False, "Groups must be a list"
    
    return True, ""

class CHORDSONG_OT_Append_Config(bpy.types.Operator, ImportHelper):
    bl_idname = "chordsong.append_config"
    bl_label = "Append Config"
    bl_description = "Merge another config file with your current configuration. Conflict checker will run automatically."

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        try:
            # Read and validate the file
            with open(self.filepath, "r", encoding="utf-8") as f:
                file_content = f.read()
            
            try:
                data = loads_json(file_content)
            except Exception as ex:
                self.report({"ERROR"}, f"Invalid JSON file: {ex}")
                return {"CANCELLED"}
            
            # Validate it's a Chordsong config (silently, just log warnings)
            is_valid, error_msg = _validate_chordsong_config(data)
            
            if not is_valid:
                # Show warning but proceed anyway
                self.report({"WARNING"}, f"File validation warning: {error_msg}")
            
            p._chordsong_suspend_autosave = True
            warns = apply_config_append(p, data)
            
            # Show warnings
            for w in warns[:5]:
                self.report({"WARNING"}, w)
            
            # Trigger conflict checker after appending
            # Use a timer to ensure the UI is ready
            def trigger_conflict_check():
                bpy.ops.chordsong.check_conflicts('INVOKE_DEFAULT')
                return None
            
            bpy.app.timers.register(trigger_conflict_check, first_interval=0.5)
            
            self.report({"INFO"}, f"Config appended from {os.path.basename(self.filepath)}")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to append config: {ex}")
            return {"CANCELLED"}
        finally:
            p._chordsong_suspend_autosave = False
