"""Extractors for operators and properties from UI context."""
import re
import bpy  # type: ignore

def parse_operator_from_text(text):
    """Parse operator ID and arguments from text like 'bpy.ops.uv.weld()' or 'bpy.ops.uv.weld(type="TEST")'.

    Returns:
        Tuple (Operator ID, Arguments String) or (None, None)
    """
    if not text:
        return None, None

    # Pattern to match [bpy.ops.]module.operator_name(...)
    pattern = r'(?:bpy\.ops\.)?([a-z0-9_]+)\.([a-z0-9_]+)\s*\((.*)\)'
    match = re.search(pattern, text)
    if match:
        module = match.group(1)
        operator = match.group(2)
        kwargs = match.group(3).strip()
        return f"{module}.{operator}", kwargs

    # Fallback for just the ID if no parentheses
    pattern_no_args = r'(?:bpy\.ops\.)?([a-z0-9_]+)\.([a-z0-9_]+)'
    match = re.search(pattern_no_args, text)
    if match:
        module = match.group(1)
        operator = match.group(2)
        return f"{module}.{operator}", ""

    return None, None

def extract_multiple_from_info_panel(context):
    """Extract multiple operators from Info panel text or clipboard.
    
    Returns:
        List of (operator, kwargs) tuples.
    """
    lines = []
    
    # Try to get text from Info Panel / Clipboard
    wm = context.window_manager
    old_clipboard = wm.clipboard
    
    # Method 1: Try to get selected report text by copying it
    try:
        if hasattr(bpy.ops.info, "report_copy"):
            area = context.area
            # Ensure we target the right area if possible
            if area and area.type == 'INFO':
                with context.temp_override(area=area):
                    bpy.ops.info.report_copy()
            else:
                bpy.ops.info.report_copy()
            
            new_clipboard = wm.clipboard
            if new_clipboard and new_clipboard != old_clipboard:
                lines = new_clipboard.splitlines()
    except Exception:
        pass
    finally:
        wm.clipboard = old_clipboard

    # Method 2: If no lines from copying, check current clipboard as fallback
    if not lines and old_clipboard:
        lines = old_clipboard.splitlines()

    results = []
    for line in lines:
        op, kwargs = parse_operator_from_text(line.strip())
        if op:
            results.append((op, kwargs))
            
    return results

def extract_from_info_panel(context):
    """Try to extract operator from Info panel text or clipboard."""
    results = extract_multiple_from_info_panel(context)
    if results:
        return results[0]  # Return first for backward compatibility
    return None, None

def extract_from_button_pointer(button_pointer):
    """Try to extract operator logic from button pointer."""
    operator = None
    button_operator = None
    kwargs = ""

    if not button_pointer:
        return None, None, ""

    # Check if button_pointer has text content to parse
    if hasattr(button_pointer, 'body'):
        operator, kwargs = parse_operator_from_text(button_pointer.body)
    elif isinstance(button_pointer, str):
        operator, kwargs = parse_operator_from_text(button_pointer)

    if operator:
        return operator, None, kwargs

    # Check if button_pointer is actually an operator instance
    if hasattr(button_pointer, "bl_idname"):
        operator = button_pointer.bl_idname
        button_operator = button_pointer
    elif hasattr(button_pointer, "operator"):
        op_attr = getattr(button_pointer, "operator", None)
        if op_attr:
            if hasattr(op_attr, "bl_idname"):
                operator = op_attr.bl_idname
                button_operator = op_attr
            elif isinstance(op_attr, str):
                operator = op_attr
    elif hasattr(button_pointer, "__class__"):
        tpname = button_pointer.__class__.__name__
        if "_OT_" in tpname:
            parts = tpname.split("_OT_")
            if len(parts) == 2:
                operator = f"{parts[0].lower()}.{parts[1].lower()}"
                button_operator = button_pointer

    # Try rna_type
    if not button_operator and hasattr(button_pointer, "rna_type"):
        try:
            rna_type_name = button_pointer.rna_type.identifier
            if "_OT_" in rna_type_name:
                parts = rna_type_name.split("_OT_")
                if len(parts) == 2:
                    operator = f"{parts[0].lower()}.{parts[1].lower()}"
                    # Try to get the actual operator class
                    op_class = getattr(bpy.types, rna_type_name, None)
                    if op_class and issubclass(op_class, bpy.types.Operator):
                        try:
                            button_operator = op_class()
                        except Exception:
                            pass
        except Exception:
            pass

    return operator, button_operator, kwargs

def extract_context_path(button_prop, button_pointer):
    """Attempt to construct a context path for a property."""
    path_parts = []
    prop_name = button_prop.identifier

    if hasattr(button_pointer, "rna_type"):
        rna_type_name = button_pointer.rna_type.identifier

        # Detect View3DOverlay (overlay properties in 3D viewport)
        if "View3DOverlay" in rna_type_name:
            path_parts = ["space_data", "overlay", prop_name]

        # Detect View3DShading (shading properties)
        elif "View3DShading" in rna_type_name:
            path_parts = ["space_data", "shading", prop_name]

        # Detect SpaceView3D (space properties)
        elif "SpaceView3D" in rna_type_name:
            path_parts = ["space_data", prop_name]

        # Detect Scene
        elif "Scene" in rna_type_name:
            path_parts = ["scene", prop_name]

        # Detect World
        elif "World" in rna_type_name:
            path_parts = ["world", prop_name]

        # Detect ToolSettings
        elif "ToolSettings" in rna_type_name:
            path_parts = ["tool_settings", prop_name]

        # Detect RenderSettings
        elif "RenderSettings" in rna_type_name:
            path_parts = ["scene", "render", prop_name]

        else:
            path_parts = [prop_name]
    else:
        path_parts = [prop_name]

    return ".".join(path_parts)

def detect_editor_context(context, operator=None):
    """Auto-detect editor context based on current editor or operator prefix."""
    # Based on operator prefix
    if operator and "." in operator:
        parts = operator.split(".")
        if len(parts) == 2:
            if parts[0].lower() in ["uv", "image"]:
                return "IMAGE_EDITOR"
            elif parts[0].lower() == "node":
                return "GEOMETRY_NODE"

    # Based on current space
    space = context.space_data
    if space:
        if space.type == 'NODE_EDITOR':
            if hasattr(space, 'tree_type'):
                if space.tree_type == 'GeometryNodeTree':
                    return "GEOMETRY_NODE"
                elif space.tree_type == 'ShaderNodeTree':
                    return "SHADER_EDITOR"
                else:
                    return "SHADER_EDITOR"
            else:
                return "GEOMETRY_NODE"
        elif space.type == 'IMAGE_EDITOR':
            return "IMAGE_EDITOR"

    return "VIEW_3D"
