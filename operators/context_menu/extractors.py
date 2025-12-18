"""Extractors for operators and properties from UI context."""
import re
import bpy  # type: ignore


def parse_operator_from_text(text):
    """Parse operator ID from text like 'bpy.ops.uv.region_clustering()' or 'bpy.ops.uv.region_clustering(...)'.
    
    Args:
        text: Text string that may contain an operator call
        
    Returns:
        Operator ID string (e.g., 'uv.region_clustering') or None if not found
    """
    if not text:
        return None
    
    # Pattern to match bpy.ops.module.operator_name(...)
    # Examples:
    # - bpy.ops.uv.region_clustering()
    # - bpy.ops.uv.region_clustering(option=True)
    # - bpy.ops.mesh.primitive_cube_add(location=(0,0,0))
    pattern = r'bpy\.ops\.([a-z_]+)\.([a-z_]+)\s*\('
    match = re.search(pattern, text)
    if match:
        module = match.group(1)
        operator = match.group(2)
        return f"{module}.{operator}"
    
    return None


def extract_from_info_panel(context):
    """Try to extract operator from Info panel text or clipboard."""
    space = context.space_data
    area = context.area
    
    is_info_panel = False
    if area and hasattr(area, 'type'):
        if area.type in ('INFO', 'CONSOLE'):
            is_info_panel = True
    elif space and hasattr(space, 'type'):
        if space.type in ('INFO', 'CONSOLE'):
            is_info_panel = True
    
    operator = None
    
    if is_info_panel:
        # Method 1: Try to get selected report text by copying it
        try:
            old_clipboard = context.window_manager.clipboard
            try:
                with context.temp_override(area=area):
                    bpy.ops.info.report_copy()
                new_clipboard = context.window_manager.clipboard
                if new_clipboard and new_clipboard != old_clipboard:
                    operator = parse_operator_from_text(new_clipboard)
                    context.window_manager.clipboard = old_clipboard
                else:
                    context.window_manager.clipboard = old_clipboard
            except Exception:
                try:
                    context.window_manager.clipboard = old_clipboard
                except Exception:
                    pass
        except Exception:
            pass
        
        # Method 2: Try to access reports directly from Info area
        if not operator and area and area.type == 'INFO':
            try:
                wm = context.window_manager
                if hasattr(wm, 'reports'):
                    for report in reversed(list(wm.reports.values())[-20:] if hasattr(wm.reports, 'values') else []):
                        if hasattr(report, 'message'):
                            operator = parse_operator_from_text(report.message)
                            if operator:
                                break
            except Exception:
                pass
        
        # Method 3: Check Info panel history (console history)
        if not operator and space and hasattr(space, 'history'):
            history = space.history
            if history:
                for entry in reversed(history[-10:]):
                    if hasattr(entry, 'body'):
                        operator = parse_operator_from_text(entry.body)
                        if operator:
                            break
                    elif isinstance(entry, str):
                        operator = parse_operator_from_text(entry)
                        if operator:
                            break
    
    # Method 4: Try to get text from clipboard
    if not operator:
        try:
            clipboard = context.window_manager.clipboard
            if clipboard:
                operator = parse_operator_from_text(clipboard)
        except Exception:
            pass
            
    return operator

def extract_from_button_pointer(button_pointer):
    """Try to extract operator logic from button pointer."""
    operator = None
    button_operator = None

    if not button_pointer:
        return None, None

    # Check if button_pointer has text content to parse
    if hasattr(button_pointer, 'body'):
        operator = parse_operator_from_text(button_pointer.body)
    elif isinstance(button_pointer, str):
        operator = parse_operator_from_text(button_pointer)
    
    if operator:
        return operator, None

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

    return operator, button_operator


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
