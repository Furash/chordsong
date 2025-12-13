# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import ast
import re

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from .common import prefs


def _ast_value_to_string(node):
    """Convert an AST value node back to a Python string representation."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        elif isinstance(node.value, bool):
            return "True" if node.value else "False"
        elif node.value is None:
            return "None"
        return str(node.value)
    elif isinstance(node, ast.NameConstant):  # Python < 3.8
        if node.value is None:
            return "None"
        return str(node.value)
    elif isinstance(node, ast.Name):
        if node.id in ("True", "False", "None"):
            return node.id
        return node.id
    elif isinstance(node, ast.Str):  # Python < 3.8
        return f'"{node.s}"'
    elif isinstance(node, ast.Num):  # Python < 3.8
        return str(node.n)
    elif isinstance(node, (ast.Tuple, ast.List)):
        items = [_ast_value_to_string(item) for item in node.elts]
        bracket = "(" if isinstance(node, ast.Tuple) else "["
        close_bracket = ")" if isinstance(node, ast.Tuple) else "]"
        return f"{bracket}{', '.join(items)}{close_bracket}"
    else:
        # For other types, try to evaluate safely
        try:
            # Use ast.literal_eval if possible by converting node to code
            # This works for literals only
            import ast as ast_module
            if hasattr(ast_module, 'unparse'):  # Python 3.9+
                return ast_module.unparse(node)
            # For older Python, try to reconstruct manually
            # This is a best-effort approach
            return repr(node)
        except Exception:
            # Last resort: return a string representation
            return repr(node)


def extract_operator_and_kwargs(text: str):
    """
    Extract operator name and kwargs from a full function call.
    Example: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD')
    Returns: (operator_name, kwargs_string)
    """
    text = text.strip()
    if not text:
        return None, None
    
    # Match pattern: bpy.ops.module.operator(...)
    # or just module.operator(...)
    match = re.match(r'(?:bpy\.ops\.)?([a-zA-Z_][a-zA-Z0-9_.]*)\((.*)\)$', text, re.DOTALL)
    if not match:
        return None, None
    
    operator_name = match.group(1)
    args_text = match.group(2).strip()
    
    if not args_text:
        return operator_name, ""
    
    # Parse the arguments to extract kwargs using AST
    try:
        # Create a fake function call to parse
        fake_call = f"func({args_text})"
        tree = ast.parse(fake_call, mode='eval')
        
        if isinstance(tree.body, ast.Call):
            kwargs_parts = []
            for keyword in tree.body.keywords:
                # Format as key = value
                value_str = _ast_value_to_string(keyword.value)
                kwargs_parts.append(f"{keyword.arg} = {value_str}")
            
            kwargs_string = ", ".join(kwargs_parts)
            return operator_name, kwargs_string
    except Exception:
        # Fallback: return args as-is (user can manually fix if needed)
        pass
    
    # Fallback: return args as-is
    return operator_name, args_text


class CHORDSONG_OT_mapping_convert(bpy.types.Operator):
    bl_idname = "chordsong.mapping_convert"
    bl_label = "Convert Function Call"
    bl_options = {"INTERNAL"}

    index: IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        p.ensure_defaults()

        idx = int(self.index)
        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}
        
        m = p.mappings[idx]
        if m.mapping_type != "OPERATOR":
            self.report({"WARNING"}, "Can only convert operator mappings")
            return {"CANCELLED"}
        
        # Get the current operator field (might contain full function call)
        full_call = (m.operator or "").strip()
        if not full_call:
            self.report({"WARNING"}, "No function call to convert")
            return {"CANCELLED"}
        
        operator_name, kwargs_string = extract_operator_and_kwargs(full_call)
        
        if operator_name:
            m.operator = operator_name
            if kwargs_string:
                m.kwargs_json = kwargs_string
            
            # Try to generate a label if empty
            if not m.label or m.label == "New Chord":
                # Extract just the operator name part (last segment)
                parts = operator_name.split('.')
                if parts:
                    op_name = parts[-1].replace('_', ' ').title()
                    m.label = op_name
            
            self.report({"INFO"}, f"Converted: {operator_name}")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, "Could not parse function call")
            return {"CANCELLED"}
