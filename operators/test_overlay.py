import bpy
import time
from ..ui.overlay.render import draw_fading_overlay, draw_overlay
from ..utils.addon_package import addon_root_package

def prefs(context):
    """Get addon preferences for extension workflow."""
    package_name = addon_root_package(__package__)
    return context.preferences.addons[package_name].preferences

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
    try:
        for window in bpy.context.window_manager.windows:
            try:
                screen = window.screen
                if not screen:
                    continue
                for area in screen.areas:
                    # Don't access area.type - it can crash on destroyed areas
                    # Just try to tag_redraw and catch exceptions
                    try:
                        area.tag_redraw()
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

def _fading_test_draw_callback():
    if not _fading_test_handler_ctx:
        return

    try:
        p = prefs(bpy.context)
    except (KeyError, AttributeError):
        # Addon is being disabled/unregistered
        return
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

    try:
        p = prefs(context)
    except (KeyError, AttributeError):
        # Addon is being disabled/unregistered
        return
    if not p: return

    global _main_test_mappings

    # Regenerate mappings if count changes or list is empty/None
    target_count = p.overlay_max_items
    if not _main_test_mappings or len(_main_test_mappings) != target_count:
        _main_test_mappings = [DummyMapping(i) for i in range(target_count)]

    draw_overlay(context, p, [], _main_test_mappings)

class DummyMapping:
    """Mock mapping object for testing - 100 items total (80 regular + 20 toggles)."""
    def __init__(self, i):
        # Modifier syntax: ^ = Ctrl, ! = Alt, + = Shift, # = Win
        
        # Define 20 toggle items (every 5th item) with alternating ON/OFF states
        # Toggle ON: 󰨚  Toggle OFF: 󰨙
        toggle_indices = [4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 69, 74, 79, 84, 89, 94, 99]
        is_toggle = i in toggle_indices
        toggle_on = (toggle_indices.index(i) % 2 == 0) if is_toggle else False
        
        # Generate diverse chords - mix of single keys, modifiers, and a few nested items
        # Most have unique starting tokens so they appear at top level
        chords = [
            # Mix of folders (will show nested) and direct actions
            ("m", "Modeling"),           # Folder - will show m x, m w, m s below
            ("m x", "X-Ray"),            # Nested under 'm'
            ("m w", "Wireframe"),        # Nested under 'm'  
            ("m s", "Snap"),             # Nested under 'm'
            ("g", "General"),            # Toggle - Folder
            ("g x", "X-Ray View"),       # Nested under 'g'
            ("g o", "Overlays"),         # Nested under 'g'
            ("g c", "Cavity"),           # Nested under 'g'
            ("g n", "Normals"),          # Toggle - nested under 'g'
            ("g f", "Face Orient"),      # Nested under 'g'
            # Unique top-level items (different starting keys)
            ("e", "Extrude"),
            ("i", "Inset"),
            ("b", "Bevel"),
            ("l", "Loop Cut"),
            ("^s", "Quick Save"),        # Toggle
            ("^z", "Undo"),
            ("^+z", "Redo"),
            ("^c", "Copy"),
            ("^v", "Paste"),
            ("!d", "Duplicate"),         # Toggle
            ("+a", "Add Menu"),
            ("x", "Delete"),
            ("h", "Hide"),
            ("!h", "Unhide"),
            ("^a", "Select All"),        # Toggle
            ("!a", "Deselect"),
            ("^i", "Invert Select"),
            ("f", "Fill"),
            ("k", "Knife Tool"),
            ("j", "Join"),               # Toggle
            # Some more nested for 's' prefix
            ("s", "Shading"),            # Folder
            ("s s", "Smooth"),           # Nested under 's'
            ("s f", "Flat"),             # Nested under 's'
            ("s a", "Auto Smooth"),      # Nested under 's'
            ("s n", "Recalc Normals"),   # Toggle - nested
            # More unique top-level
            ("t", "Transform Menu"),
            ("r", "Rotate"),
            ("w", "Move"),
            ("z", "Scale"),
            ("^m", "Mirror"),            # Toggle
            ("p", "Proportional"),
            ("o", "Origin"),
            ("^p", "Parent"),
            ("!p", "Clear Parent"),
            ("n", "New"),                # Toggle
            ("^n", "New File"),
            ("^o", "Open"),
            ("!s", "Save As"),
            ("^+s", "Save Copy"),
            ("q", "Quit"),               # Toggle
            # Some nested for 'c' prefix
            ("c", "Camera"),             # Folder
            ("c v", "Cam to View"),      # Nested under 'c'
            ("c s", "Set Active"),       # Nested under 'c'
            ("c t", "Track"),            # Nested under 'c'
            ("c z", "Zoom"),             # Toggle - nested
            # More unique
            ("u", "Unwrap"),
            ("^u", "UV Reset"),
            ("a", "Animate"),
            ("^k", "Keyframe"),
            ("!k", "Clear Keys"),        # Toggle
            ("d", "Subdivide"),
            ("^d", "Duplicate Linked"),
            ("y", "Redo"),
            ("!z", "Redo Alt"),
            ("^y", "Redo Panel"),        # Toggle
            # Few more nested for 'v' prefix
            ("v", "View"),               # Folder
            ("v f", "Frame All"),        # Nested under 'v'
            ("v s", "Frame Selected"),   # Nested under 'v'
            ("v c", "View Camera"),      # Nested under 'v'
            ("v a", "View All"),         # Toggle - nested
            # More unique top-level
            ("/", "Search"),
            ("^f", "Find"),
            ("^h", "Replace"),
            ("^g", "Go To"),
            ("^r", "Render"),            # Toggle
            ("^b", "Border Render"),
            ("^+b", "Box Select"),
            ("^e", "Export"),
            ("^+e", "Export FBX"),
            ("!", "Info"),               # Toggle
            ("^j", "Join as Shape"),
            ("^l", "Make Links"),
            ("^+l", "Link Transfer"),
            ("^t", "Track Menu"),
            ("^+t", "Track Clear"),      # Toggle
            # Few remaining
            ("1", "Front View"),
            ("3", "Side View"),
            ("7", "Top View"),
            ("0", "Camera View"),
            ("5", "Ortho Toggle"),       # Toggle
            ("2", "Rotate View"),
            ("4", "Pan View"),
            ("6", "Right View"),
            ("8", "Back View"),
            ("9", "Opposite"),           # Toggle
            (".", "Frame"),
            (",", "Zoom All"),
            (";", "Local View"),
            ("'", "Lock Camera"),
            ("[", "Prev Frame"),         # Toggle
            ("]", "Next Frame"),
            ("-", "Zoom Out"),
            ("=", "Zoom In"),
            ("`", "Console"),
            ("~", "Manipulator"),        # Toggle
        ]
        
        if i < len(chords):
            self.chord, base_label = chords[i]
        else:
            self.chord = f"k{i+1}"
            base_label = f"Action {i+1}"
        
        # Apply toggle state to label if this is a toggle item
        if is_toggle:
            icon = "󰨚" if toggle_on else "󰨙"
            self.label = f"{base_label}  {icon}"
        else:
            self.label = base_label

        # Common Nerd Font icons (Save, Folder, Code, Play, Gear, Search, Image, Bug)
        icons = ["\uf0c7", "\uf07b", "\uf1c9", "\uf04b", "\uf013", "\uf002", "\uf02e", "\uf188"]
        self.icon = icons[i % len(icons)]

        # Assign groups based on position (10 items per group)
        groups = ["Modeling", "General", "Shading", "Transform", "Select", 
                  "Render", "Camera", "Edit", "UV", "Animation"]
        self.group = groups[(i // 10) % len(groups)]

        self.context = "VIEW_3D"
        self.enabled = True
        # Mark toggle items as CONTEXT_TOGGLE type
        self.mapping_type = "CONTEXT_TOGGLE" if is_toggle else "OPERATOR"

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
