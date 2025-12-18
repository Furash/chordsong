# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import StringProperty, EnumProperty  # type: ignore

from .common import prefs, schedule_autosave_safe
import re


class CHORDSONG_OT_Context_Menu(bpy.types.Operator):
    """Add a chord mapping for this UI element"""
    bl_idname = "chordsong.context_menu"
    bl_label = "Add Chord Mapping"
    bl_options = {"INTERNAL"}

    operator: StringProperty(
        name="Operator",
        description="Operator command to assign",
        default="",
    )
    
    kwargs: StringProperty(
        name="Parameters",
        description="Operator parameters",
        default="",
    )
    
    context_path: StringProperty(
        name="Context Path",
        description="Context path for property toggle",
        default="",
    )
    
    mapping_type: StringProperty(
        name="Mapping Type",
        description="Type of mapping (OPERATOR or CONTEXT_TOGGLE)",
        default="OPERATOR",
    )
    
    chord: StringProperty(
        name="Chord",
        description="Keyboard chord to trigger this operator",
        default="",
    )
    
    name: StringProperty(
        name="Name",
        description="Name/label for the mapping",
        default="",
    )
    
    group: StringProperty(
        name="Group",
        description="Group for organizing the mapping",
        default="",
    )
    
    editor_context: EnumProperty(
        name="Editor Context",
        description="Editor context where this chord mapping will be active",
        items=(
            ("VIEW_3D", "3D View", "Active in 3D View editor", "VIEW3D", 0),
            ("GEOMETRY_NODE", "Geometry Nodes", "Active in Geometry Nodes editor", "GEOMETRY_NODES", 1),
            ("SHADER_EDITOR", "Shader Editor", "Active in Shader Editor", "NODE_MATERIAL", 2),
        ),
        default="VIEW_3D",
    )

    def _parse_operator_from_text(self, text):
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
    
    def _suggest_chord(self, group, label):
        """Generate a smart chord suggestion based on group and label.
        
        Args:
            group: The group name (e.g., "Object", "View")
            label: The label/operator name (e.g., "Select All")
            
        Returns:
            A non-conflicting chord string (e.g., "o a" for Object + Select All)
        """
        p = prefs(bpy.context)
        
        # Get existing chords for conflict checking
        existing_chords = set()
        for m in p.mappings:
            if m.enabled:
                existing_chords.add(m.chord.strip().lower())
        
        # Helper to clean and extract initials
        def get_initials(text, max_chars=3):
            """Extract initials from text, max max_chars characters."""
            if not text:
                return ""
            # Remove common words and split
            words = text.lower().split()
            # Filter out very common words
            common = {"the", "a", "an", "to", "for", "of", "in", "on", "at", "by"}
            words = [w for w in words if w not in common]
            if not words:
                return ""
            
            # Get first letter of each word, up to max_chars
            initials = "".join(w[0] for w in words[:max_chars])
            return initials[:max_chars]
        
        # Generate base chord from group + label
        group_initial = get_initials(group, 1)
        label_initials = get_initials(label, 2)
        
        # Helper to add spaces between characters
        def spacify(text):
            """Add spaces between each character."""
            return " ".join(text) if text else ""
        
        if not group_initial or not label_initials:
            # Fallback to just label initials
            label_initials = get_initials(label, 3)
            if not label_initials:
                return ""
            candidates = [spacify(label_initials)]
        else:
            # Try various combinations
            candidates = [
                f"{group_initial} {spacify(label_initials)}",  # e.g., "o s a" for Object + Select All
                f"{group_initial} {label_initials[0]}",  # e.g., "o s"
                spacify(label_initials),  # Just label initials with spaces
            ]
        
        # Find first non-conflicting chord
        for candidate in candidates:
            if candidate and candidate not in existing_chords:
                return candidate
        
        # If all conflict, try adding a number suffix
        for candidate in candidates:
            if not candidate:
                continue
            for i in range(1, 10):
                numbered = f"{candidate} {i}"
                if numbered not in existing_chords:
                    return numbered
        
        # Last resort: return empty and let user decide
        return ""
    
    def invoke(self, context, event):
        """Extract operator or property info and show dialog.
        
        This works when right-clicking on:
        - Operator buttons in the UI
        - Items in the F3 search menu
        - Menu items
        - Boolean properties (for toggle)
        - Info panel text (e.g., bpy.ops.uv.region_clustering())
        """
        # Reset all properties to default values to avoid carrying over old data
        self.operator = ""
        self.kwargs = ""
        self.context_path = ""
        self.mapping_type = "OPERATOR"
        self.chord = ""
        self.name = ""
        self.group = ""
        self.editor_context = "VIEW_3D"
        
        button_operator = getattr(context, "button_operator", None)
        button_prop = getattr(context, "button_prop", None)
        button_pointer = getattr(context, "button_pointer", None)
        
        # Try to extract operator from Info panel text if we're in Info panel
        # Check if we can get selected text or the line that was right-clicked
        if not button_operator and not self.operator:
            # Check if we're in Info panel context
            # Info panel can be accessed through CONSOLE space type or through area type
            space = context.space_data
            area = context.area
            
            # Check if we're in Info/Console area
            is_info_panel = False
            if area and hasattr(area, 'type'):
                # Info panel is typically in a CONSOLE area
                if area.type == 'CONSOLE':
                    is_info_panel = True
            elif space and hasattr(space, 'type'):
                if space.type == 'CONSOLE':
                    is_info_panel = True
            
            if is_info_panel:
                # Try to get text from Info panel
                try:
                    # Method 1: Check Info panel history (console history)
                    if space and hasattr(space, 'history'):
                        history = space.history
                        if history:
                            # Check the last few entries for operator calls
                            for entry in reversed(history[-10:]):  # Check last 10 entries
                                if hasattr(entry, 'body'):
                                    parsed_op = self._parse_operator_from_text(entry.body)
                                    if parsed_op:
                                        self.operator = parsed_op
                                        break
                                elif isinstance(entry, str):
                                    parsed_op = self._parse_operator_from_text(entry)
                                    if parsed_op:
                                        self.operator = parsed_op
                                        break
                    
                    # Method 2: Try to get selected text from clipboard
                    # User might have selected text before right-clicking
                    try:
                        clipboard = context.window_manager.clipboard
                        if clipboard:
                            parsed_op = self._parse_operator_from_text(clipboard)
                            if parsed_op:
                                self.operator = parsed_op
                    except Exception:
                        pass
                except Exception:
                    pass
            
            # Also try to parse from any text that might be in button_pointer
            if not self.operator and button_pointer:
                # Check if button_pointer has text content
                if hasattr(button_pointer, 'body'):
                    parsed_op = self._parse_operator_from_text(button_pointer.body)
                    if parsed_op:
                        self.operator = parsed_op
                elif isinstance(button_pointer, str):
                    parsed_op = self._parse_operator_from_text(button_pointer)
                    if parsed_op:
                        self.operator = parsed_op
        
        # Try to extract operator ID from alternative sources when button_operator is not available
        # This handles cases where Blender doesn't set button_operator for some search menu items
        if not button_operator and button_pointer:
            # Check if button_pointer is actually an operator instance
            # First check if it has bl_idname (direct operator)
            if hasattr(button_pointer, "bl_idname"):
                self.operator = button_pointer.bl_idname
                button_operator = button_pointer
            # Check if button_pointer has an operator attribute
            elif hasattr(button_pointer, "operator"):
                op_attr = getattr(button_pointer, "operator", None)
                if op_attr:
                    if hasattr(op_attr, "bl_idname"):
                        self.operator = op_attr.bl_idname
                        button_operator = op_attr
                    elif isinstance(op_attr, str):
                        self.operator = op_attr
            # Check if button_pointer's class name indicates it's an operator
            elif hasattr(button_pointer, "__class__"):
                tpname = button_pointer.__class__.__name__
                # Check if it's an operator class (contains _OT_)
                if "_OT_" in tpname:
                    parts = tpname.split("_OT_")
                    if len(parts) == 2:
                        idname = f"{parts[0].lower()}.{parts[1].lower()}"
                        self.operator = idname
                        button_operator = button_pointer
            # Try to extract operator ID from RNA type identifier
            if not button_operator and hasattr(button_pointer, "rna_type"):
                try:
                    rna_type_name = button_pointer.rna_type.identifier
                    # Check if it's an operator type (contains _OT_)
                    if "_OT_" in rna_type_name:
                        parts = rna_type_name.split("_OT_")
                        if len(parts) == 2:
                            idname = f"{parts[0].lower()}.{parts[1].lower()}"
                            self.operator = idname
                            # Try to get the actual operator class
                            op_class = getattr(bpy.types, rna_type_name, None)
                            if op_class and issubclass(op_class, bpy.types.Operator):
                                # Create a temporary instance to get properties
                                try:
                                    temp_op = op_class()
                                    button_operator = temp_op
                                except Exception:
                                    pass
                except Exception:
                    pass
        
        # Check if it's a boolean property (for context toggle)
        if button_prop and button_pointer and not button_operator:
            # Try to build context path for the property
            try:
                # Check if it's a boolean property
                if button_prop.type == 'BOOLEAN':
                    self.mapping_type = "CONTEXT_TOGGLE"
                    
                    # Build the context path more robustly
                    path_parts = []
                    prop_name = button_prop.identifier
                    
                    # Try to determine the path based on the pointer's type
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
                        
                        # Fallback: just use the property name if we can't determine context
                        else:
                            path_parts = [prop_name]
                    else:
                        # No rna_type, just use property name
                        path_parts = [prop_name]
                    
                    self.context_path = ".".join(path_parts)
                    
                    # Auto-fill name from property
                    self.name = button_prop.name or button_prop.identifier.replace("_", " ").title()
                    self.group = "Toggle"
                    
                    # Generate smart chord suggestion
                    self.chord = self._suggest_chord(self.group, self.name)
                    
                    # Auto-detect context based on current editor
                    space = context.space_data
                    if space:
                        if space.type == 'NODE_EDITOR':
                            if hasattr(space, 'tree_type'):
                                if space.tree_type == 'GeometryNodeTree':
                                    self.editor_context = "GEOMETRY_NODE"
                                elif space.tree_type == 'ShaderNodeTree':
                                    self.editor_context = "SHADER_EDITOR"
                                else:
                                    self.editor_context = "SHADER_EDITOR"
                            else:
                                self.editor_context = "GEOMETRY_NODE"
                        else:
                            self.editor_context = "VIEW_3D"
                    else:
                        self.editor_context = "VIEW_3D"
                    
                    # Show dialog for entering chord
                    return context.window_manager.invoke_props_dialog(self, width=450)
            except Exception:
                # Fall through to operator detection
                pass
        
        # If we parsed an operator from Info panel text, process it
        if self.operator and not button_operator:
            # We have an operator ID but no button_operator instance
            # Try to extract group and name from operator ID
            if "." in self.operator:
                parts = self.operator.split(".")
                if len(parts) == 2:
                    group_name = parts[0].replace("_", " ").title()
                    self.group = group_name
                    label_name = parts[1].replace("_", " ").title()
                    self.name = label_name
                    # Auto-detect context based on operator prefix
                    if parts[0].lower() in ["uv", "image"]:
                        self.editor_context = "IMAGE_EDITOR"
                    elif parts[0].lower() == "node":
                        self.editor_context = "GEOMETRY_NODE"
                    else:
                        # Detect based on current editor
                        space = context.space_data
                        if space:
                            if space.type == 'NODE_EDITOR':
                                if hasattr(space, 'tree_type'):
                                    if space.tree_type == 'GeometryNodeTree':
                                        self.editor_context = "GEOMETRY_NODE"
                                    elif space.tree_type == 'ShaderNodeTree':
                                        self.editor_context = "SHADER_EDITOR"
                                    else:
                                        self.editor_context = "SHADER_EDITOR"
                                else:
                                    self.editor_context = "GEOMETRY_NODE"
                            elif space.type == 'IMAGE_EDITOR':
                                self.editor_context = "IMAGE_EDITOR"
                            else:
                                self.editor_context = "VIEW_3D"
                        else:
                            self.editor_context = "VIEW_3D"
                    # Generate smart chord suggestion
                    self.chord = self._suggest_chord(self.group, self.name)
                    # Show dialog for entering chord
                    return context.window_manager.invoke_props_dialog(self, width=450)
        
        # Try operator detection
        if button_operator:
            self.mapping_type = "OPERATOR"
            
            # Get the operator's class name (e.g., "OBJECT_OT_select_all")
            tpname = button_operator.__class__.__name__
            
            # Convert from class name to bl_idname format
            # e.g., "OBJECT_OT_select_all" -> "object.select_all"
            if "_OT_" in tpname:
                parts = tpname.split("_OT_")
                idname = f"{parts[0].lower()}.{parts[1].lower()}"
                self.operator = idname
                
                # Auto-fill Group from the first part (e.g., "OBJECT" -> "Object")
                group_name = parts[0].replace("_", " ").title()
                self.group = group_name
                
                # Auto-fill Name from the second part (e.g., "select_all" -> "Select All")
                label_name = parts[1].replace("_", " ").title()
                self.name = label_name
                
                # Auto-detect context based on operator
                if parts[0].lower() == "node":
                    # Node operators default to Geometry Nodes
                    self.editor_context = "GEOMETRY_NODE"
                else:
                    # Detect based on current editor
                    space = context.space_data
                    if space:
                        if space.type == 'NODE_EDITOR':
                            if hasattr(space, 'tree_type'):
                                if space.tree_type == 'GeometryNodeTree':
                                    self.editor_context = "GEOMETRY_NODE"
                                elif space.tree_type == 'ShaderNodeTree':
                                    self.editor_context = "SHADER_EDITOR"
                                else:
                                    self.editor_context = "SHADER_EDITOR"
                            else:
                                self.editor_context = "GEOMETRY_NODE"
                        else:
                            self.editor_context = "VIEW_3D"
                    else:
                        self.editor_context = "VIEW_3D"
                
                # Try to get operator properties for kwargs
                args = []
                node_type_value = None
                keys = button_operator.keys()
                if keys:
                    for k in keys:
                        try:
                            v = getattr(button_operator, k)
                            
                            # For node operators with 'type' parameter, auto-detect context and extract label
                            if k == 'type' and isinstance(v, str) and parts[0].lower() == "node":
                                node_type_value = v
                                if v.startswith('ShaderNode'):
                                    self.editor_context = "SHADER_EDITOR"
                                elif v.startswith('GeometryNode'):
                                    self.editor_context = "GEOMETRY_NODE"
                            
                            # Simple value conversion for parameters
                            if isinstance(v, str):
                                args.append(f'{k} = "{v}"')
                            elif isinstance(v, bool):
                                args.append(f'{k} = {v}')
                            elif isinstance(v, (int, float)):
                                args.append(f'{k} = {v}')
                        except Exception:
                            continue
                
                # Generate better label for node operators
                if parts[0].lower() == "node" and node_type_value:
                    import re
                    # Clean up node type names
                    node_name = node_type_value
                    # Remove common prefixes
                    for prefix in ['ShaderNode', 'GeometryNode', 'CompositorNode', 'TextureNode']:
                        if node_name.startswith(prefix):
                            node_name = node_name[len(prefix):]
                            break
                    
                    # Convert from CamelCase to Title Case with spaces
                    node_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', node_name)
                    node_name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', node_name)
                    self.name = node_name
                
                # Store the kwargs for the operator
                if args:
                    self.kwargs = ", ".join(args)
                
                # Generate smart chord suggestion
                self.chord = self._suggest_chord(self.group, self.name)
                
                # Show dialog for entering chord
                return context.window_manager.invoke_props_dialog(self, width=450)
        
        # If we couldn't detect an operator automatically, still show the dialog
        # but with empty operator field so user can manually enter it
        # This handles cases where Blender doesn't set button_operator for some search menu items
        if self.operator:
            # We have an operator ID but no button_operator instance
            # Try to extract group and name from operator ID
            if "." in self.operator:
                parts = self.operator.split(".")
                if len(parts) == 2:
                    group_name = parts[0].replace("_", " ").title()
                    self.group = group_name
                    label_name = parts[1].replace("_", " ").title()
                    self.name = label_name
                    # Auto-detect context based on operator prefix
                    if parts[0].lower() == "uv" or parts[0].lower() == "image":
                        self.editor_context = "IMAGE_EDITOR"
                    elif parts[0].lower() == "node":
                        self.editor_context = "GEOMETRY_NODE"
                    else:
                        # Detect based on current editor
                        space = context.space_data
                        if space:
                            if space.type == 'NODE_EDITOR':
                                if hasattr(space, 'tree_type'):
                                    if space.tree_type == 'GeometryNodeTree':
                                        self.editor_context = "GEOMETRY_NODE"
                                    elif space.tree_type == 'ShaderNodeTree':
                                        self.editor_context = "SHADER_EDITOR"
                                    else:
                                        self.editor_context = "SHADER_EDITOR"
                                else:
                                    self.editor_context = "GEOMETRY_NODE"
                            elif space.type == 'IMAGE_EDITOR':
                                self.editor_context = "IMAGE_EDITOR"
                            else:
                                self.editor_context = "VIEW_3D"
                        else:
                            self.editor_context = "VIEW_3D"
                    # Generate smart chord suggestion
                    self.chord = self._suggest_chord(self.group, self.name)
                    # Show dialog for entering chord
                    return context.window_manager.invoke_props_dialog(self, width=450)
        
        # If we still don't have an operator, show a dialog to manually enter it
        # This handles cases where Blender doesn't expose operator info through context
        self.mapping_type = "OPERATOR"
        # Show dialog - the operator field will be empty and user can fill it in
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context):
        """Draw the dialog UI"""
        layout = self.layout
        
        col = layout.column(align=True)
        if self.mapping_type == "CONTEXT_TOGGLE":
            col.label(text=f"Toggle: {self.context_path}", icon="CHECKBOX_HLT")
        else:
            if self.operator:
                col.label(text=f"Operator: {self.operator}", icon="SETTINGS")
            else:
                # Show help text when operator is not detected
                col.label(text="Operator not detected automatically", icon="INFO")
                col.label(text="Please enter the operator ID manually", icon="BLANK1")
                col.separator()
                col.label(text="Example: uv.region_clustering", icon="BLANK1")
                col.label(text="(You can see the Python command in the search menu)", icon="BLANK1")
                col.separator()
        
        # Operator input field (show prominently if empty)
        if not self.operator:
            col.label(text="Operator ID:", icon="SETTINGS")
            col.prop(self, "operator", text="")
            col.separator()
        
        # Chord input (main field)
        col.label(text="Enter Chord:")
        col.prop(self, "chord", text="")
        col.separator()
        
        # Editor context selector
        col.label(text="Editor Context:")
        row = col.row(align=True)
        row.prop(self, "editor_context", expand=True)
        col.separator()
        
        # Name and Group
        col.prop(self, "name", text="Label")
        col.prop(self, "group", text="Group")

    def execute(self, context: bpy.types.Context):
        p = prefs(context)
        
        if not self.chord:
            self.report({'WARNING'}, "Please enter a chord")
            return {"CANCELLED"}
        
        if self.mapping_type == "CONTEXT_TOGGLE":
            if not self.context_path:
                self.report({'WARNING'}, "No context path specified")
                return {"CANCELLED"}
            
            # Create new context toggle mapping
            m = p.mappings.add()
            m.enabled = True
            m.chord = self.chord
            m.label = self.name if self.name else "Toggle"
            m.group = self.group if self.group else ""
            m.context = self.editor_context
            m.context_path = self.context_path
            m.mapping_type = "CONTEXT_TOGGLE"
            
            msg = f"Added chord '{self.chord}' for toggle: {self.context_path}"
        else:
            if not self.operator:
                self.report({'WARNING'}, "No operator specified. Please enter an operator ID (e.g., 'uv.region_clustering')")
                return {"CANCELLED"}
            
            # If name/group weren't auto-filled, try to extract them from operator ID
            if not self.name or not self.group:
                if "." in self.operator:
                    parts = self.operator.split(".")
                    if len(parts) == 2:
                        if not self.group:
                            self.group = parts[0].replace("_", " ").title()
                        if not self.name:
                            self.name = parts[1].replace("_", " ").title()
            
            # Auto-detect context if not already set
            if self.editor_context == "VIEW_3D" and "." in self.operator:
                parts = self.operator.split(".")
                if len(parts) == 2:
                    if parts[0].lower() in ["uv", "image"]:
                        self.editor_context = "IMAGE_EDITOR"
                    elif parts[0].lower() == "node":
                        self.editor_context = "GEOMETRY_NODE"
            
            # Create new operator mapping
            m = p.mappings.add()
            m.enabled = True
            m.chord = self.chord
            m.label = self.name if self.name else "New Chord"
            m.group = self.group if self.group else ""
            m.context = self.editor_context
            m.operator = self.operator
            m.call_context = "INVOKE_DEFAULT"
            m.kwargs_json = self.kwargs if self.kwargs else ""
            m.mapping_type = "OPERATOR"
            
            msg = f"Added chord '{self.chord}' for: {self.operator}"
        
        # Move the new item to the top of the list
        last_index = len(p.mappings) - 1
        if last_index > 0:
            p.mappings.move(last_index, 0)
        
        schedule_autosave_safe(p, delay_s=5.0)
        
        # Open preferences to show the new mapping
        try:
            bpy.ops.chordsong.open_prefs('INVOKE_DEFAULT')
        except Exception:
            pass
        
        self.report({'INFO'}, msg)
        return {"FINISHED"}


class CHORDSONG_MT_button_context:
    """Base menu class for button context menu"""
    bl_label = "Button Context Menu"
    
    def draw(self, context):
        self.layout.separator()


def button_context_menu_draw(self, context):
    """Draw function that adds our button to the right-click context menu.
    
    This works for:
    - Regular operator buttons in the UI
    - Items in the search menu (F3)
    - Menu items
    - Boolean properties (for toggle)
    - Info panel text (e.g., bpy.ops.uv.region_clustering())
    
    Note: We always show the menu item when we're in WM_MT_button_context,
    even if we can't detect an operator. The invoke method will try to extract
    operator information from various sources, including parsing from Info panel text.
    """
    layout = self.layout
    
    # Always show the menu item when we're in the button context menu
    # This ensures it appears for all search menu items, even when button_operator isn't set
    # The invoke method will handle extracting operator information from various sources
    layout.separator()
    layout.operator(
        CHORDSONG_OT_Context_Menu.bl_idname,
        text="Add Chord Mapping",
        icon="KEYINGSET"
    )


def register_context_menu():
    """Register the context menu hook.
    
    Creates WM_MT_button_context if it doesn't exist (for compatibility)
    and appends our draw function to it.
    """
    # Create WM_MT_button_context if it doesn't exist
    if not hasattr(bpy.types, "WM_MT_button_context"):
        # Dynamically create the menu type
        tp = type("WM_MT_button_context", (CHORDSONG_MT_button_context, bpy.types.Menu), {})
        bpy.utils.register_class(tp)
    
    # Append our draw function to the context menu
    bpy.types.WM_MT_button_context.append(button_context_menu_draw)


def unregister_context_menu():
    """Unregister the context menu hook"""
    if hasattr(bpy.types, "WM_MT_button_context"):
        try:
            bpy.types.WM_MT_button_context.remove(button_context_menu_draw)
        except Exception:
            pass
