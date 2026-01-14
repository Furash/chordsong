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
        
        # Define toggle items - ensure at least 5 ON and 5 OFF visible at top level
        # Toggle ON: 󰨚  Toggle OFF: 󰨙
        # Put toggles at visible indices: 2, 5, 7, 10, 12, 15, 17, 20, 22, 25, etc.
        toggle_indices = [2, 5, 7, 10, 12, 15, 17, 20, 22, 25, 28, 31, 34, 37, 40, 43, 46, 49, 52, 55]
        is_toggle = i in toggle_indices
        # First 5 ON, next 5 OFF, then alternating
        if is_toggle:
            idx_pos = toggle_indices.index(i)
            if idx_pos < 5:
                toggle_on = True  # First 5 are ON
            elif idx_pos < 10:
                toggle_on = False  # Next 5 are OFF
            else:
                toggle_on = (idx_pos % 2 == 0)  # Then alternate
        else:
            toggle_on = False
        
        # Generate diverse chords - ensure toggle items are at top level
        # Indices 2, 5, 7, 10, 12, 15, 17, 20, 22, 25 are toggles
        chords = [
            # Index 0-1: Regular items
            ("m", "Modeling"),           # 0: Folder
            ("m x", "X-Ray"),            # 1: Nested under 'm'
            ("e", "Extrude"),            # 2: Toggle ON
            ("m w", "Wireframe"),        # 3: Nested under 'm'  
            ("m s", "Snap"),             # 4: Nested under 'm'
            ("w", "Wireframe Mode"),     # 5: Toggle ON
            ("g", "General"),            # 6: Folder
            ("o", "Overlays"),           # 7: Toggle ON
            ("g x", "X-Ray View"),       # 8: Nested under 'g'
            ("g o", "Cavity"),           # 9: Nested under 'g'
            ("s", "Shading"),            # 10: Toggle ON
            ("g c", "Face Orient"),      # 11: Nested under 'g'
            ("n", "Normals"),            # 12: Toggle ON
            ("i", "Inset"),              # 13: Regular
            ("b", "Bevel"),              # 14: Regular
            ("x", "X-Ray Toggle"),       # 15: Toggle OFF
            ("l", "Loop Cut"),           # 16: Regular
            ("z", "Proportional"),       # 17: Toggle OFF
            ("^z", "Undo"),              # 18: Regular
            ("^+z", "Redo"),             # 19: Regular
            ("a", "Auto Smooth"),        # 20: Toggle OFF
            ("^c", "Copy"),              # 21: Regular
            ("v", "Backface Culling"),   # 22: Toggle OFF
            ("^v", "Paste"),             # 23: Regular
            ("!d", "Duplicate"),         # 24: Regular
            ("h", "Hidden Wires"),       # 25: Toggle OFF
            ("+a", "Add Menu"),          # 26: Regular
            ("d", "Delete"),             # 27: Regular
            ("^h", "Hide"),              # 28: Toggle (alternating - ON)
            ("!h", "Unhide"),            # 29: Regular
            ("!a", "Deselect"),          # 31: Toggle (alternating - ON)
            ("^i", "Invert Select"),     # 32: Regular
            ("f", "Fill"),               # 33: Regular
            ("k", "Knife Tool"),         # 34: Toggle (alternating - OFF)
            ("j", "Join"),               # 35: Regular
            ("t", "Transform Menu"),     # 36: Regular
            ("r", "Rotate"),             # 37: Toggle (alternating - ON)
            ("u", "Move"),               # 38: Regular
            ("y", "Scale"),              # 39: Regular
            ("p", "Proportional Edit"),  # 41: Regular
            ("q", "Origin"),             # 42: Regular
            ("^p", "Parent"),            # 43: Toggle (alternating - ON)
            ("!p", "Clear Parent"),      # 44: Regular
            ("^n", "New File"),          # 45: Regular
            ("^o", "Open"),              # 46: Toggle (alternating - OFF)
            ("!s", "Save As"),           # 47: Regular
            ("^+s", "Save Copy"),        # 48: Regular
            ("^u", "Unwrap"),            # 49: Toggle (alternating - ON)
            ("^k", "Keyframe"),          # 50: Regular
            ("!k", "Clear Keys"),        # 51: Regular
            ("^d", "Duplicate Linked"),  # 52: Toggle (alternating - OFF)
            ("!z", "Redo Alt"),          # 53: Regular
            ("^y", "Redo Panel"),        # 54: Regular
            ("/", "Search"),             # 55: Toggle (alternating - ON)
            ("^f", "Find"),              # 56: Regular
            ("^g", "Go To"),             # 57: Regular
            ("^r", "Render"),            # 58: Regular
            ("^b", "Border Render"),     # 59: Regular
            ("^+b", "Box Select"),       # 60: Regular
            ("^e", "Export"),            # 61: Regular
            ("^+e", "Export FBX"),       # 62: Regular
            ("!", "Info"),               # 63: Regular
            ("^j", "Join as Shape"),     # 64: Regular
            ("^l", "Make Links"),        # 65: Regular
            ("^+l", "Link Transfer"),    # 66: Regular
            ("^t", "Track Menu"),        # 67: Regular
            ("1", "Front View"),         # 68: Regular
            ("3", "Side View"),          # 69: Regular
            ("7", "Top View"),           # 70: Regular
            ("0", "Camera View"),        # 71: Regular
            ("5", "Ortho Toggle"),       # 72: Regular
            ("2", "Rotate View"),        # 73: Regular
            ("4", "Pan View"),           # 74: Regular
            ("6", "Right View"),         # 75: Regular
            ("8", "Back View"),          # 76: Regular
            (".", "Frame"),              # 77: Regular
            (",", "Zoom All"),           # 78: Regular
            (";", "Local View"),         # 79: Regular
            ("'", "Lock Camera"),        # 80: Regular
            ("[", "Prev Frame"),         # 81: Regular
            ("]", "Next Frame"),         # 82: Regular
            ("-", "Zoom Out"),           # 83: Regular
            ("=", "Zoom In"),            # 84: Regular
            ("`", "Console"),            # 85: Regular
            ("~", "Manipulator"),        # 86: Regular
            ("9", "Opposite View"),      # 87: Regular
            ("@", "Annotations"),        # 88: Regular
            ("#", "Statistics"),         # 89: Regular
            ("$", "Asset Browser"),      # 90: Regular
            ("%", "Geometry Nodes"),     # 91: Regular
            ("&", "Compositor"),         # 92: Regular
            ("*", "Shader Editor"),      # 93: Regular
            ("(", "UV Editor"),          # 94: Regular
            (")", "Movie Clip"),         # 95: Regular
            ("_", "Spreadsheet"),        # 96: Regular
            ("+", "Preferences"),        # 97: Regular
            ("{", "Timeline"),           # 98: Regular
            ("}", "NLA Editor"),         # 99: Regular
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
