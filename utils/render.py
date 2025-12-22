"""Common rendering utilities for draw handlers and overlays."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore

# Keys to capture from context for viewport operations
VIEWPORT_CONTEXT_KEYS = ("area", "region", "space_data", "window", "screen")

class ContextWrapper:
    """Wrapper to access dictionary keys as attributes, falling back to bpy.context."""
    def __init__(self, ctx_dict):
        self._ctx = ctx_dict

    def __getattr__(self, name):
        if name in self._ctx:
            return self._ctx[name]
        return getattr(bpy.context, name)

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

def validate_viewport_context(ctx_viewport) -> dict:
    """Validate that captured viewport context is still valid.

    After undo or other operations, context objects (area, region, etc.) can become
    invalid. This function checks if they're still valid by testing property access.
    We don't check membership in parent collections because after undo, objects may
    be recreated but still be functionally valid for temp_override.

    Args:
        ctx_viewport: Dictionary of captured context values

    Returns:
        Validated context dictionary, or empty dict if context is invalid
    """
    if not ctx_viewport:
        return {}

    try:
        # Check if window is still valid by trying to access its properties
        window = ctx_viewport.get("window")
        if window:
            try:
                # Try to access a property to see if window is still valid
                _ = window.screen
            except (AttributeError, RuntimeError, ReferenceError):
                return {}

        # Check if screen is still valid
        screen = ctx_viewport.get("screen")
        if screen:
            try:
                # Try to access a property to see if screen is still valid
                _ = screen.areas
            except (AttributeError, RuntimeError, ReferenceError):
                return {}

        # Check if area is still valid
        area = ctx_viewport.get("area")
        if area:
            try:
                # Try to access properties to see if area is still valid
                _ = area.type
                _ = area.spaces
            except (AttributeError, RuntimeError, ReferenceError):
                return {}

        # Check if region is still valid
        region = ctx_viewport.get("region")
        if region:
            try:
                # Try to access a property to see if region is still valid
                _ = region.type
            except (AttributeError, RuntimeError, ReferenceError):
                return {}

        # Check if space_data is still valid
        space_data = ctx_viewport.get("space_data")
        if space_data:
            try:
                # Try to access a property to see if space_data is still valid
                _ = space_data.type
            except (AttributeError, RuntimeError, ReferenceError):
                return {}

        # All objects are still valid (can access properties)
        # Note: We don't check membership in parent collections because after undo,
        # Blender may recreate UI objects, making membership checks fail even though
        # the objects are still valid for use in temp_override
        return ctx_viewport

    except (AttributeError, RuntimeError, ReferenceError):
        # Context objects are invalid (freed by Blender)
        return {}

def calculate_scale_factor(context) -> float:
    """Calculate UI scale factor for fonts and spacing, respecting Blender UI settings.

    Args:
        context: Blender context object

    Returns:
        Scale factor as a float
    """
    try:
        # Access preferences via bpy.context for robustness in draw handlers
        prefs = bpy.context.preferences
        
        # Respect UI Scale (System > Interface > Resolution Scale)
        # Note: view.ui_scale is often 1.0, while system.dpi reflects the Resolution Scale.
        ui_scale = getattr(prefs.view, "ui_scale", 1.0)
        
        # Respect DPI (System > Interface > Resolution Scale also affects this)
        # Standard DPI is 72. 
        dpi = prefs.system.dpi
        
        # Respect Pixel Size (1 for standard, 2 for Retina/HighDPI)
        # This is the most reliable way to scale for High DPI.
        pixel_size = getattr(prefs.system, "pixel_size", 1.0)
        
        # Respect Line Width (System > Interface > Line Width)
        # This affects the 'thickness' of the UI.
        # Enums: 'THIN', 'AUTO', 'THICK'
        line_width_mult = 1.0
        if hasattr(prefs.system, "line_width"):
            lw = prefs.system.line_width
            if lw == 'THICK':
                line_width_mult = 1.25
            elif lw == 'THIN':
                line_width_mult = 0.85

        # Base scale factor combines DPI and UI scale
        scale = ui_scale * (dpi / 72.0)
        
        # Ensure it's at least pixel_size
        scale = max(scale, pixel_size)
        
        return scale * line_width_mult
    except Exception:
        try:
            return bpy.context.preferences.system.dpi / 72.0
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
    elif pos == "CENTER_TOP":
        return (region_w - block_w) // 2 + pad_x, region_h - pad_y
    elif pos == "CENTER_BOTTOM":
        return (region_w - block_w) // 2 + pad_x, pad_y + block_h
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

        # Use execution context from history if available
        if hasattr(entry, 'execution_context') and entry.execution_context:
            ctx_viewport = entry.execution_context
            # Must validate because the area might be closed
            valid_ctx = validate_viewport_context(ctx_viewport)
            if not valid_ctx:
                return False, "Operator area not found"
        else:
            # Fallback for old history entries or missing context
            ctx_viewport = capture_viewport_context(context)
            valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

        if call_ctx == "INVOKE_DEFAULT":
            if valid_ctx:
                try:
                    with bpy.context.temp_override(**valid_ctx):
                        result_set = opfn('INVOKE_DEFAULT', **kwargs)
                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                    # Context became invalid, fall back to default context
                    result_set = opfn('INVOKE_DEFAULT', **kwargs)
            else:
                result_set = opfn('INVOKE_DEFAULT', **kwargs)
        else:
            if valid_ctx:
                try:
                    with bpy.context.temp_override(**valid_ctx):
                        result_set = opfn('EXEC_DEFAULT', **kwargs)
                except (TypeError, RuntimeError, AttributeError, ReferenceError):
                    # Context became invalid, fall back to default context
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

        # Use execution context from history if available
        if hasattr(entry, 'execution_context') and entry.execution_context:
            ctx_viewport = entry.execution_context
            # Must validate because the area might be closed
            valid_ctx = validate_viewport_context(ctx_viewport)
            if not valid_ctx:
                return False, "Operator area not found"
        else:
            # Fallback for old history entries or missing context
            ctx_viewport = capture_viewport_context(context)
            valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

        with open(entry.python_file, 'r', encoding='utf-8') as f:
            script_text = f.read()

        if valid_ctx:
            try:
                with bpy.context.temp_override(**valid_ctx):
                    exec(compile(script_text, entry.python_file, 'exec'))  # pylint: disable=exec-used
            except (TypeError, RuntimeError, AttributeError, ReferenceError):
                # Context became invalid, fall back to default context
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
        # Use execution context from history if available
        effective_context = context

        if hasattr(entry, 'execution_context') and entry.execution_context:
            ctx_viewport = entry.execution_context
            # Must validate because the area might be closed
            valid_ctx = validate_viewport_context(ctx_viewport)
            if not valid_ctx:
                return False, "Operator area not found"

        else:
            # Fallback for old history entries or missing context
            ctx_viewport = capture_viewport_context(context)
            valid_ctx = validate_viewport_context(ctx_viewport) if ctx_viewport else None

        if valid_ctx:
            effective_context = ContextWrapper(valid_ctx)

        def do_toggle():
            parts = entry.context_path.split('.')
            obj = effective_context
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

        if valid_ctx:
            try:
                with bpy.context.temp_override(**valid_ctx):
                    new_value = do_toggle()
            except (TypeError, RuntimeError, AttributeError, ReferenceError):
                # Context became invalid, fall back to default context
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
        return False, str(e)
