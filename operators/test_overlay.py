import bpy
import time
from ..ui.overlay.render import draw_fading_overlay, draw_overlay
from ..utils.render import DrawHandlerManager

def prefs(context):
    """Get addon preferences."""
    try:
        package_name = __package__.split(".")[0] if __package__ else "chordsong"
        return context.preferences.addons[package_name].preferences
    except (KeyError, AttributeError):
        # Fallback search
        for name, addon in context.preferences.addons.items():
            if "chordsong" in name:
                return addon.preferences
        return None

# Global storage for the fading test handler
_fading_test_handler = None
_fading_test_handler_ctx = None

def disable_test_overlays():
    """Disable active test overlays."""
    global _fading_test_handler, _fading_test_handler_ctx
    global _main_test_handler, _main_test_ctx, _main_test_mappings

    dirty = False

    if _fading_test_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_fading_test_handler, 'WINDOW')
        _fading_test_handler = None
        _fading_test_handler_ctx = None
        dirty = True

    if _main_test_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_main_test_handler, 'WINDOW')
        _main_test_handler = None
        _main_test_ctx = None
        _main_test_mappings = []
        dirty = True

    if dirty:
        tag_redraw_all_views()

def tag_redraw_all_views():
    """Tag all relevant areas for redraw to ensure overlay visibility."""
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D', 'NODE_EDITOR', 'IMAGE_EDITOR'}:
                area.tag_redraw()

def _fading_test_draw_callback():
    if not _fading_test_handler_ctx:
        return

    p = prefs(bpy.context)
    # Mock data for testing
    chord_text = "a b c"
    label = "Test Operator Action"
    icon = "\uf04b" # Play icon (Nerd Font)

    # We pass a fake start time that is always current time, so elapsed is 0
    # effective duration is infinite as long as we keep updating start_time
    draw_fading_overlay(
        bpy.context, p,
        chord_text, label, icon,
        start_time=time.time(),
        fade_duration=10.0
    )

class CHORDSONG_OT_TestFadingOverlay(bpy.types.Operator):
    """Toggle a test fading overlay that stays visible for adjustment."""
    bl_idname = "chordsong.test_fading_overlay"
    bl_label = "Test Fading Overlay"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _fading_test_handler, _fading_test_handler_ctx

        if _fading_test_handler is not None:
            # Remove existing handler
            bpy.types.SpaceView3D.draw_handler_remove(_fading_test_handler, 'WINDOW')
            _fading_test_handler = None
            _fading_test_handler_ctx = None
            tag_redraw_all_views()
            self.report({'INFO'}, "Test overlay hidden")
        else:
            # Add new handler
            _fading_test_handler_ctx = context
            _fading_test_handler = bpy.types.SpaceView3D.draw_handler_add(
                _fading_test_draw_callback, (), 'WINDOW', 'POST_PIXEL'
            )
            tag_redraw_all_views()
            self.report({'INFO'}, "Test overlay shown (Run again to hide)")

        return {'FINISHED'}

# Main Overlay Test

_main_test_handler = None
_main_test_ctx = None
_main_test_mappings = []

def _main_test_draw_callback():
    if not _main_test_ctx:
        return

    # Use bpy.context which is correct during draw
    context = bpy.context
    # Check if context is valid
    if not context or not hasattr(context, "preferences"):
        return

    p = prefs(context)
    if not p: return

    global _main_test_mappings

    # Regenerate mappings if count changes or list is empty/None
    target_count = p.overlay_max_items
    if not _main_test_mappings or len(_main_test_mappings) != target_count:
        _main_test_mappings = [DummyMapping(i) for i in range(target_count)]

    draw_overlay(context, p, [], _main_test_mappings)

class DummyMapping:
    """Mock mapping object for testing."""
    def __init__(self, i):
        # Generate unique starting token so all items appear in the top-level list.
        # Vary FIRST token length to test column width calculation

        if i % 3 == 0:
             # Long first token (simulating modifiers)
             prefix = f"ctrl+shift+k{i+1:02d}"
             self.chord = f"{prefix} a b c"
             self.label = f"Long Token {i+1:02d}"
        elif i % 3 == 1:
             # Short first token (simulating single digit)
             prefix = f"{i+1}"
             self.chord = f"{prefix}"
             self.label = f"Short {i+1:02d}"
        else:
             # Standard first token
             prefix = f"k{i+1:02d}"
             self.chord = f"{prefix} x"
             self.label = f"Test Operator {i+1:02d}"

        # Common Nerd Font icons (Save, Folder, Code, Play, Gear, Search, Image, Bug)
        icons = ["\uf0c7", "\uf07b", "\uf1c9", "\uf04b", "\uf013", "\uf002", "\uf02e", "\uf188"]
        self.icon = icons[i % len(icons)]

        # Assign groups to test grouping visualization
        if i < 5:
            self.group = "Common"
        elif i < 15:
            self.group = "Modeling"
        else:
            self.group = "Rendering"

        self.context = "VIEW_3D"
        self.enabled = True

class CHORDSONG_OT_TestMainOverlay(bpy.types.Operator):
    """Show the main overlay filled with dummy items for testing layout."""
    bl_idname = "chordsong.test_main_overlay"
    bl_label = "Test Main Overlay"
    bl_options = {'REGISTER'}

    def execute(self, context):
        global _main_test_handler, _main_test_ctx, _main_test_mappings

        if _main_test_handler is not None:
            # Remove
            bpy.types.SpaceView3D.draw_handler_remove(_main_test_handler, 'WINDOW')
            _main_test_handler = None
            _main_test_ctx = None
            _main_test_mappings = []
            tag_redraw_all_views()
            self.report({'INFO'}, "Test Main Overlay hidden")
        else:
            # Add
            _main_test_ctx = context
            # Initial populate
            p = prefs(context)
            if p:
                _main_test_mappings = [DummyMapping(i) for i in range(p.overlay_max_items)]

            _main_test_handler = bpy.types.SpaceView3D.draw_handler_add(
                _main_test_draw_callback, (), 'WINDOW', 'POST_PIXEL'
            )
            tag_redraw_all_views()
            self.report({'INFO'}, "Test Main Overlay shown (Run again to hide)")

        return {'FINISHED'}
