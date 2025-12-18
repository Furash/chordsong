# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import ast
import re

import bpy  # type: ignore
from bpy.props import IntProperty  # type: ignore

from ..common import prefs


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
                
                # Store raw value for label generation
                # Try to extract string values without quotes
                if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
                    kwargs_dict[keyword.arg] = keyword.value.value
                elif isinstance(keyword.value, ast.Str):  # Python < 3.8
                    kwargs_dict[keyword.arg] = keyword.value.s
            
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

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
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
        
        operator_name, kwargs_string, kwargs_dict = extract_operator_and_kwargs(full_call)
        
        if operator_name:
            m.operator = operator_name
            if kwargs_string:
                m.kwargs_json = kwargs_string
            
            # Generate a smart label based on operator type and parameters
            m.label = self._generate_smart_label(operator_name, kwargs_dict)
            
            # Auto-detect context based on operator
            m.context = self._detect_context_from_operator(operator_name, kwargs_dict)
            
            self.report({"INFO"}, f"Converted: {operator_name}")
            return {"FINISHED"}
        else:
            self.report({"WARNING"}, "Could not parse function call")
            return {"CANCELLED"}
    
    def _detect_context_from_operator(self, operator_name: str, kwargs_dict: dict) -> str:
        """Detect the appropriate editor context based on the operator."""
        parts = operator_name.split('.')
        
        # Node operators
        if len(parts) >= 1 and parts[0] == 'node':
            # Check if there's a 'type' parameter that indicates shader vs geometry nodes
            if 'type' in kwargs_dict:
                node_type = kwargs_dict['type']
                if node_type.startswith('ShaderNode'):
                    return "SHADER_EDITOR"
                elif node_type.startswith('GeometryNode'):
                    return "GEOMETRY_NODE"
                elif node_type.startswith('CompositorNode'):
                    return "SHADER_EDITOR"  # Compositor uses shader editor context
            
            # Default node operations to Geometry Nodes
            # (user can change if needed)
            return "GEOMETRY_NODE"
        
        # Default to 3D View for all other operators
        return "VIEW_3D"
    
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
