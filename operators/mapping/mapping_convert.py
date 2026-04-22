# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import ast
import re

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs

def _ast_value_to_string(node):
    """Convert an AST value node back to a Python string representation.

    Targets Python 3.9+ (Blender 5.0 ships 3.11). ast.NameConstant / ast.Str /
    ast.Num compat branches were removed — they were only relevant on
    Python <3.8 and are deprecated/removed aliases in 3.12+.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        elif isinstance(node.value, bool):
            return "True" if node.value else "False"
        elif node.value is None:
            return "None"
        return str(node.value)
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, (ast.Tuple, ast.List)):
        items = [_ast_value_to_string(item) for item in node.elts]
        bracket = "(" if isinstance(node, ast.Tuple) else "["
        close_bracket = ")" if isinstance(node, ast.Tuple) else "]"
        return f"{bracket}{', '.join(items)}{close_bracket}"
    # Fallback: use ast.unparse (Python 3.9+). If that fails, last-ditch repr.
    try:
        return ast.unparse(node)
    except Exception:
        return repr(node)

def extract_operator_and_kwargs(text: str):
    """
    Extract operator name and kwargs from a full function call.
    Example: bpy.ops.mesh.primitive_cube_add(enter_editmode=False, align='WORLD')
    Returns: (operator_name, kwargs_string, kwargs_dict)
    """
    text = text.strip()
    if not text:
        return None, None, None

    # Match pattern: bpy.ops.module.operator(...)
    # or just module.operator(...)
    match = re.match(r'(?:bpy\.ops\.)?([a-zA-Z_][a-zA-Z0-9_.]*)\((.*)\)$', text, re.DOTALL)
    if not match:
        return None, None, None

    operator_name = match.group(1)
    args_text = match.group(2).strip()

    if not args_text:
        return operator_name, "", {}

    # Parse the arguments to extract kwargs using AST
    try:
        # Create a fake function call to parse
        fake_call = f"func({args_text})"
        tree = ast.parse(fake_call, mode='eval')

        if isinstance(tree.body, ast.Call):
            kwargs_parts = []
            kwargs_dict = {}

            for keyword in tree.body.keywords:
                # Format as key = value
                value_str = _ast_value_to_string(keyword.value)
                kwargs_parts.append(f"{keyword.arg} = {value_str}")

                # Store raw value for label generation — only string literals.
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    kwargs_dict[keyword.arg] = keyword.value.value

            kwargs_string = ", ".join(kwargs_parts)
            return operator_name, kwargs_string, kwargs_dict
    except Exception:
        # Fallback: return args as-is (user can manually fix if needed)
        pass

    # Fallback: return args as-is
    return operator_name, args_text, {}

class CHORDSONG_OT_Mapping_Convert(bpy.types.Operator):
    bl_idname = "chordsong.mapping_convert"
    bl_label = "Convert Function Call"
    bl_description = "Parse full operator call (e.g. bpy.ops.mesh.primitive_cube_add(size=2)) into operator name and parameters"
    bl_options = {"INTERNAL"}

    index: IntProperty(default=-1)
    sub_index: IntProperty(default=-1)

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        idx = int(self.index)
        sub_idx = int(self.sub_index)

        if idx < 0 or idx >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        m = p.mappings[idx]
        if m.mapping_type != "OPERATOR":
            self.report({"WARNING"}, "Can only convert operator mappings")
            return {"CANCELLED"}

        # Target object: either the mapping itself or a sub-operator
        target = m
        if sub_idx >= 0:
            if sub_idx < len(m.sub_operators):
                target = m.sub_operators[sub_idx]
            else:
                self.report({"WARNING"}, "Invalid sub-operator index")
                return {"CANCELLED"}

        # Get the current operator field (might contain full function call)
        full_call = (target.operator or "").strip()
        if not full_call:
            self.report({"WARNING"}, "No function call to convert")
            return {"CANCELLED"}

        operator_name, kwargs_string, kwargs_dict = extract_operator_and_kwargs(full_call)

        if operator_name:
            target.operator = operator_name
            if kwargs_string:
                target.kwargs_json = kwargs_string

            # If this is the primary operator, update label and context
            if sub_idx < 0:
                # Generate a smart label based on operator type and parameters
                m.label = self._generate_smart_label(operator_name, kwargs_dict)

                # Suggest chord only if:
                # 1. There is no existing chord, OR
                # 2. The existing chord conflicts with another mapping (exact or prefix)
                try:
                    from ..context_menu.suggester import suggest_chord, has_prefix_conflict
                    # Determine group
                    group = m.group
                    if not group and "." in operator_name:
                        group = operator_name.split(".")[0].replace("_", " ").title()
                    
                    current_chord = m.chord.strip().lower()
                    should_suggest = False
                    
                    # Suggest if no chord exists
                    if not current_chord:
                        should_suggest = True
                    else:
                        # Check if current chord conflicts with another enabled mapping
                        # (including prefix conflicts)
                        other_chords = set()
                        for other_m in p.mappings:
                            if other_m != m and other_m.enabled and other_m.chord.strip():
                                other_chords.add(other_m.chord.strip().lower())
                        
                        if has_prefix_conflict(current_chord, other_chords):
                            should_suggest = True
                    
                    if should_suggest:
                        m.chord = suggest_chord(group, m.label)
                    
                    if not m.group and group:
                        m.group = group
                except Exception:
                    pass

            self.report({"INFO"}, f"Converted: {operator_name}")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, "Could not parse function call")
            return {"CANCELLED"}

    def _generate_smart_label(self, operator_name: str, kwargs_dict: dict) -> str:
        """Generate a smart label from operator name and parameters."""
        parts = operator_name.split('.')

        # Check if this is a node operator (node.add_node, node.add_search, etc.)
        if len(parts) >= 2 and parts[0] == 'node':
            # Look for 'type' parameter in kwargs
            if 'type' in kwargs_dict:
                node_type = kwargs_dict['type']

                # Clean up node type names
                # Remove common prefixes: ShaderNode, GeometryNode, CompositorNode, etc.
                for prefix in ['ShaderNode', 'GeometryNode', 'CompositorNode', 'TextureNode']:
                    if node_type.startswith(prefix):
                        node_type = node_type[len(prefix):]
                        break

                # Convert from CamelCase to Title Case with spaces
                # e.g., "Blackbody" stays "Blackbody", "MixRGB" becomes "Mix RGB"
                label = re.sub(r'([a-z])([A-Z])', r'\1 \2', node_type)
                label = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', label)  # Handle RGB, HSV, etc.

                return label

            # If no type parameter, check for 'node_tree' (for group operations)
            if 'node_tree' in kwargs_dict:
                tree_name = kwargs_dict['node_tree']
                return f"Node: {tree_name}"

        # Check for mesh primitives
        if len(parts) >= 2 and parts[0] == 'mesh' and parts[1].startswith('primitive_'):
            primitive = parts[1].replace('primitive_', '').replace('_', ' ').title()
            return f"Add {primitive}"

        # Check for object operations
        if len(parts) >= 2 and parts[0] == 'object':
            op_name = parts[1].replace('_', ' ').title()
            # Special cases
            if op_name == 'Delete':
                return 'Delete Object'
            elif op_name == 'Duplicate':
                return 'Duplicate Object'
            return op_name

        # Default: use the operator name (last part, title case)
        if parts:
            op_name = parts[-1].replace('_', ' ').title()
            return op_name

        return "Operator"
