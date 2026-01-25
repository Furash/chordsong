"""Add/remove parameter rows for operator mappings."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,relative-beyond-top-level

import bpy  # type: ignore

from ...ui.prefs import _on_mapping_changed
from ..common import prefs


def _get_operator_ptr(prefs_obj, mapping_index: int, operator_index: int):
    """Return mapping or sub-operator pointer.

    operator_index:
      - 0 => primary operator (mapping itself)
      - 1..n => sub_operators[operator_index-1]
    """
    if mapping_index < 0 or mapping_index >= len(prefs_obj.mappings):
        return None

    m = prefs_obj.mappings[mapping_index]
    if operator_index <= 0:
        return m

    sub_idx = operator_index - 1
    if sub_idx < 0 or sub_idx >= len(getattr(m, "sub_operators", [])):
        return None
    return m.sub_operators[sub_idx]


class CHORDSONG_OT_OperatorParam_Add(bpy.types.Operator):
    """Add a new operator parameter row."""

    bl_idname = "chordsong.operator_param_add"
    bl_label = "Add Operator Parameter"
    bl_options = {"REGISTER", "UNDO"}

    mapping_index: bpy.props.IntProperty()
    operator_index: bpy.props.IntProperty(default=0)

    def execute(self, context):
        prefs_obj = prefs(context)
        ptr = _get_operator_ptr(prefs_obj, int(self.mapping_index), int(self.operator_index))
        if ptr is None or not hasattr(ptr, "operator_params"):
            return {"CANCELLED"}

        ptr.operator_params.add()
        _on_mapping_changed(self, context)
        return {"FINISHED"}


class CHORDSONG_OT_OperatorParam_Remove(bpy.types.Operator):
    """Remove an operator parameter row."""

    bl_idname = "chordsong.operator_param_remove"
    bl_label = "Remove Operator Parameter"
    bl_options = {"REGISTER", "UNDO"}

    mapping_index: bpy.props.IntProperty()
    operator_index: bpy.props.IntProperty(default=0)
    param_index: bpy.props.IntProperty()

    def execute(self, context):
        prefs_obj = prefs(context)
        ptr = _get_operator_ptr(prefs_obj, int(self.mapping_index), int(self.operator_index))
        if ptr is None or not hasattr(ptr, "operator_params"):
            return {"CANCELLED"}

        i = int(self.param_index)
        if i < 0 or i >= len(ptr.operator_params):
            return {"CANCELLED"}

        ptr.operator_params.remove(i)
        _on_mapping_changed(self, context)
        return {"FINISHED"}

