"""Common rendering utilities for draw handlers and overlays."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore


# Keys to capture from context for viewport operations
VIEWPORT_CONTEXT_KEYS = ("area", "region", "space_data", "window", "screen")


def capture_viewport_context(context) -> dict:
    """Capture viewport context for use in deferred operations.
    
    Args:
        context: Blender context object
        
    Returns:
        Dictionary of captured context values
    """
    ctx_viewport = {}
    for key in VIEWPORT_CONTEXT_KEYS:
        val = getattr(context, key, None)
        if val is not None:
            ctx_viewport[key] = val
    return ctx_viewport


def calculate_scale_factor(context) -> float:
    """Calculate UI scale factor for fonts and spacing.
    
    Args:
        context: Blender context object
        
    Returns:
        Scale factor as a float
    """
    try:
        ui_scale = getattr(context.preferences.view, "ui_scale", 1.0)
        dpi = context.preferences.system.dpi
        return ui_scale * (dpi / 72.0)
    except Exception:
        try:
            return context.preferences.system.dpi / 72.0
        except Exception:
            return 1.0


def calculate_overlay_position(prefs, region_w, region_h, block_w, block_h, pad_x, pad_y):
    """Calculate overlay position based on anchor setting.
    
    Args:
        prefs: Addon preferences with overlay_position
        region_w: Region width
        region_h: Region height
        block_w: Block width
        block_h: Block height
        pad_x: Horizontal padding
        pad_y: Vertical padding
        
    Returns:
        Tuple of (x, y) coordinates
    """
    pos = prefs.overlay_position
    if pos == "TOP_RIGHT":
        return region_w - pad_x - block_w, region_h - pad_y
    elif pos == "BOTTOM_LEFT":
        return pad_x, pad_y + block_h
    elif pos == "BOTTOM_RIGHT":
        return region_w - pad_x - block_w, pad_y + block_h
    else:  # TOP_LEFT
        return pad_x, region_h - pad_y


class DrawHandlerManager:
    """Manages draw handlers for modal operators."""
    
    def __init__(self):
        self._draw_handle = None
        self._area = None
        self._region = None
        self._space_type = None
    
    def ensure_handler(self, context, callback, prefs):
        """Set up draw handler if not already active."""
        if not prefs.overlay_enabled or self._draw_handle is not None:
            return
        
        self._area = context.area
        self._region = context.region
        
        # Determine which space type to use
        space = context.space_data
        if space and space.type == 'NODE_EDITOR':
            # For Node Editor (Shader Editor, Geometry Nodes)
            self._space_type = bpy.types.SpaceNodeEditor
        elif space and space.type == 'IMAGE_EDITOR':
            self._space_type = bpy.types.SpaceImageEditor
        else:
            # Default to 3D View
            self._space_type = bpy.types.SpaceView3D
        
        self._draw_handle = self._space_type.draw_handler_add(
            callback, (), "WINDOW", "POST_PIXEL"
        )
    
    def remove_handler(self):
        """Remove draw handler if active."""
        if self._draw_handle is None:
            return
        try:
            if self._space_type:
                self._space_type.draw_handler_remove(self._draw_handle, "WINDOW")
            else:
                bpy.types.SpaceView3D.draw_handler_remove(self._draw_handle, "WINDOW")
        except Exception:
            pass
        self._draw_handle = None
        self._space_type = None
    
    def tag_redraw(self):
        """Request redraw for the area."""
        if self._area:
            try:
                self._area.tag_redraw()
            except Exception:
                pass
    
    @property
    def area(self):
        return self._area
    
    @property
    def region(self):
        return self._region


def execute_history_entry_operator(context, entry):
    """Execute an operator from history entry.
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        mod_name, fn_name = entry.operator.split(".", 1)
        opmod = getattr(bpy.ops, mod_name)
        opfn = getattr(opmod, fn_name)
        
        kwargs = entry.kwargs or {}
        call_ctx = entry.call_context or "EXEC_DEFAULT"
        
        # Capture viewport context
        ctx_viewport = capture_viewport_context(context)
        
        if call_ctx == "INVOKE_DEFAULT":
            if ctx_viewport:
                with bpy.context.temp_override(**ctx_viewport):
                    result_set = opfn('INVOKE_DEFAULT', **kwargs)
            else:
                result_set = opfn('INVOKE_DEFAULT', **kwargs)
        else:
            if ctx_viewport:
                with bpy.context.temp_override(**ctx_viewport):
                    result_set = opfn('EXEC_DEFAULT', **kwargs)
            else:
                result_set = opfn('EXEC_DEFAULT', **kwargs)
        
        # Check if successful
        if result_set and ('FINISHED' in result_set or 'CANCELLED' not in result_set):
            return True, None
        return False, None
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to execute operator {entry.operator}: {e}"
        print(f"Chord Song: {error_msg}")
        traceback.print_exc()
        return False, error_msg


def execute_history_entry_script(context, entry):
    """Execute a Python script from history entry.
    
    Returns:
        tuple: (success: bool, error_message: str or None)
    """
    try:
        import os
        if not os.path.exists(entry.python_file):
            error_msg = f"Script file not found: {entry.python_file}"
            print(f"Chord Song: {error_msg}")
            return False, error_msg
        
        # Capture viewport context
        ctx_viewport = capture_viewport_context(context)
        
        with open(entry.python_file, 'r', encoding='utf-8') as f:
            script_text = f.read()
        
        if ctx_viewport:
            with bpy.context.temp_override(**ctx_viewport):
                exec(compile(script_text, entry.python_file, 'exec'))  # pylint: disable=exec-used
        else:
            exec(compile(script_text, entry.python_file, 'exec'))  # pylint: disable=exec-used
        
        return True, None
        
    except Exception as e:
        import traceback
        error_msg = f"Failed to execute script {entry.python_file}: {e}"
        print(f"Chord Song: {error_msg}")
        traceback.print_exc()
        return False, error_msg


def execute_history_entry_toggle(context, entry):
    """Execute a context toggle from history entry.
    
    Returns:
        tuple: (success: bool, new_value: bool or None)
    """
    try:
        # Capture viewport context
        ctx_viewport = capture_viewport_context(context)
        
        def do_toggle():
            parts = entry.context_path.split('.')
            obj = bpy.context
            for part in parts[:-1]:
                obj = getattr(obj, part, None)
                if obj is None:
                    return None
            prop_name = parts[-1]
            if not hasattr(obj, prop_name):
                return None
            current_value = getattr(obj, prop_name)
            if not isinstance(current_value, bool):
                return None
            setattr(obj, prop_name, not current_value)
            return not current_value
        
        if ctx_viewport:
            with bpy.context.temp_override(**ctx_viewport):
                new_value = do_toggle()
        else:
            new_value = do_toggle()
        
        if new_value is not None:
            return True, new_value
        return False, None
        
    except Exception as e:
        import traceback
        print(f"Chord Song: Failed to toggle context '{entry.context_path}': {e}")
        traceback.print_exc()
        return False, None
