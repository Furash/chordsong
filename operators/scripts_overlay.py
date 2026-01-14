"""Scripts overlay operator for quick script access."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error

import os
import bpy  # type: ignore
from ..ui.overlay import draw_overlay
from .common import prefs


class CHORDSONG_OT_ScriptsOverlay(bpy.types.Operator):
    """Show overlay with available scripts from scripts folder"""
    
    bl_idname = "chordsong.scripts_overlay"
    bl_label = "Scripts Overlay"
    bl_options = {'REGISTER'}
    
    _draw_handles = {}
    _buffer = None
    _scripts_list = []
    _invoke_area_ptr = None
    
    def _ensure_draw_handler(self, context: bpy.types.Context):
        p = prefs(context)
        if not p.overlay_enabled or self._draw_handles:
            return
        
        self._invoke_area_ptr = context.area.as_pointer() if context.area else None
        
        # Register handlers for all major space types
        self._draw_handles = {}
        supported_types = [
            bpy.types.SpaceView3D,
            bpy.types.SpaceNodeEditor,
            bpy.types.SpaceImageEditor,
            bpy.types.SpaceSequenceEditor,
        ]
        
        for st in supported_types:
            handle = st.draw_handler_add(self._draw_callback, (), "WINDOW", "POST_PIXEL")
            self._draw_handles[st] = handle
    
    def _remove_draw_handler(self):
        if not self._draw_handles:
            return
        for st, handle in self._draw_handles.items():
            try:
                st.draw_handler_remove(handle, "WINDOW")
            except Exception:
                pass
        self._draw_handles = {}
    
    def _tag_redraw(self):
        """Tag all relevant areas for redraw."""
        try:
            for window in bpy.context.window_manager.windows:
                try:
                    screen = window.screen
                    if not screen:
                        continue
                    for area in screen.areas:
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass
    
    def _draw_callback(self):
        """Draw callback for the scripts overlay."""
        context = bpy.context
        try:
            p = prefs(context)
        except (KeyError, AttributeError):
            return
        if not p.overlay_enabled:
            return
        
        # Only draw in the area where overlay was invoked
        if self._invoke_area_ptr is not None and context.area is not None:
            try:
                if context.area.as_pointer() != self._invoke_area_ptr:
                    return
            except Exception:
                pass
        
        # Create fake mappings from scripts list for overlay rendering
        from ..ui import prefs as prefs_module
        fake_mappings = []
        
        # Create a temporary PropertyGroup subclass for fake mappings
        for i, (script_name, script_path) in enumerate(self._scripts_list):
            # Create a simple object to mimic a mapping
            class FakeMapping:
                def __init__(self, chord, label, icon="FILE_SCRIPT"):
                    self.chord = chord
                    self.label = label
                    self.icon = icon
                    self.group = "Scripts"
                    self.context = "ALL"
                    self.mapping_type = "PYTHON_FILE"
                    self.python_file = script_path
                    self.enabled = True
                    self.kwargs_json = ""
                    self.call_context = "EXEC_DEFAULT"
                    self.sub_items = []
                    self.sub_operators = []
                    self.script_params = []
            
            # Assign number keys 1-9, then letters
            if i < 9:
                chord = str(i + 1)
            elif i < 35:
                chord = chr(ord('a') + (i - 9))
            else:
                chord = f"s {i - 34}"  # s 1, s 2, etc.
            
            fake_mappings.append(FakeMapping(chord, script_name))
        
        # Use the overlay rendering with fake mappings
        buffer_tokens = self._buffer or []
        draw_overlay(context, p, buffer_tokens, fake_mappings)
    
    def invoke(self, context: bpy.types.Context, _event: bpy.types.Event):
        """Start scripts overlay modal operation."""
        p = prefs(context)
        p.ensure_defaults()
        
        # Get scripts folder
        scripts_folder = p.scripts_folder
        if not scripts_folder or not os.path.isdir(scripts_folder):
            self.report({'WARNING'}, "Scripts folder not set or doesn't exist. Set it in preferences.")
            return {'CANCELLED'}
        
        # Check if custom scripts are enabled
        if not p.allow_custom_user_scripts:
            self.report({'WARNING'}, "Custom user scripts are disabled. Enable them in preferences.")
            return {'CANCELLED'}
        
        # Scan scripts folder for .py files
        self._scripts_list = []
        try:
            for filename in sorted(os.listdir(scripts_folder)):
                if filename.endswith('.py') and not filename.startswith('__'):
                    script_path = os.path.join(scripts_folder, filename)
                    script_name = filename[:-3]  # Remove .py extension
                    self._scripts_list.append((script_name, script_path))
        except Exception as e:
            self.report({'ERROR'}, f"Failed to scan scripts folder: {e}")
            return {'CANCELLED'}
        
        if not self._scripts_list:
            self.report({'INFO'}, "No scripts found in scripts folder")
            return {'CANCELLED'}
        
        self._buffer = []
        self._ensure_draw_handler(context)
        context.window_manager.modal_handler_add(self)
        self._tag_redraw()
        return {"RUNNING_MODAL"}
    
    def _finish(self, context: bpy.types.Context):
        self._remove_draw_handler()
        self._tag_redraw()
    
    def cancel(self, context: bpy.types.Context):
        """Clean up when operator is interrupted."""
        self._finish(context)
    
    def modal(self, context: bpy.types.Context, event: bpy.types.Event):
        # Cancel keys
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}
        
        # Number or letter key pressed
        if event.value == "PRESS":
            # Handle 1-9 for first 9 scripts
            if event.type in {f"NUMPAD_{i}" for i in range(1, 10)} | {f"{i}" for i in range(1, 10)}:
                try:
                    # Extract the number
                    if event.type.startswith("NUMPAD_"):
                        idx = int(event.type[-1]) - 1
                    else:
                        idx = int(event.type) - 1
                    
                    if idx < len(self._scripts_list):
                        script_name, script_path = self._scripts_list[idx]
                        self._finish(context)
                        self._execute_script(context, script_path, script_name)
                        return {"FINISHED"}
                except (ValueError, IndexError):
                    pass
            
            # Handle A-Z for scripts 10-35
            elif event.type in {chr(i) for i in range(ord('A'), ord('Z') + 1)}:
                idx = ord(event.type) - ord('A') + 9
                if idx < len(self._scripts_list):
                    script_name, script_path = self._scripts_list[idx]
                    self._finish(context)
                    self._execute_script(context, script_path, script_name)
                    return {"FINISHED"}
        
        return {"RUNNING_MODAL"}
    
    def _execute_script(self, context, script_path, script_name):
        """Execute a script file."""
        def execute_delayed():
            try:
                from ..utils.render import _execute_script_via_text_editor, capture_viewport_context
                
                # Capture viewport context
                ctx_viewport = capture_viewport_context(context)
                
                # Execute script
                success, error_msg = _execute_script_via_text_editor(
                    script_path,
                    script_args={},
                    valid_ctx=ctx_viewport,
                    context=bpy.context
                )
                
                if not success:
                    print(f"Chord Song Scripts Overlay: {error_msg}")
                else:
                    self.report({'INFO'}, f"Executed: {script_name}")
                    
            except Exception as e:
                import traceback
                print(f"Chord Song Scripts Overlay: Failed to execute script: {e}")
                traceback.print_exc()
            return None
        
        bpy.app.timers.register(execute_delayed, first_interval=0.01)


# Registration
classes = (
    CHORDSONG_OT_ScriptsOverlay,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
