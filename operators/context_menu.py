# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import StringProperty, EnumProperty  # type: ignore

from .common import prefs, schedule_autosave_safe


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

    def invoke(self, context, event):
        """Extract operator or property info and show dialog.
        
        This works when right-clicking on:
        - Operator buttons in the UI
        - Items in the F3 search menu
        - Menu items
        - Boolean properties (for toggle)
        """
        button_operator = getattr(context, "button_operator", None)
        button_prop = getattr(context, "button_prop", None)
        button_pointer = getattr(context, "button_pointer", None)
        
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
                            print(f"Chord Song: Unknown RNA type '{rna_type_name}' for property '{prop_name}'")
                            path_parts = [prop_name]
                    else:
                        # No rna_type, just use property name
                        path_parts = [prop_name]
                    
                    self.context_path = ".".join(path_parts)
                    
                    # Auto-fill name from property
                    self.name = button_prop.name or button_prop.identifier.replace("_", " ").title()
                    self.group = "Toggle"
                    
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
            except Exception as e:
                print(f"Chord Song: Failed to detect property: {e}")
                import traceback
                traceback.print_exc()
                # Fall through to operator detection
        
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
                
                # Show dialog for entering chord
                return context.window_manager.invoke_props_dialog(self, width=450)
        
        self.report({'WARNING'}, "Could not detect operator or property from context")
        return {"CANCELLED"}

    def draw(self, context):
        """Draw the dialog UI"""
        layout = self.layout
        
        col = layout.column(align=True)
        if self.mapping_type == "CONTEXT_TOGGLE":
            col.label(text=f"Toggle: {self.context_path}", icon="CHECKBOX_HLT")
        else:
            col.label(text=f"Operator: {self.operator}", icon="SETTINGS")
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
                self.report({'WARNING'}, "No operator specified")
                return {"CANCELLED"}
            
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
    """
    layout = self.layout
    
    button_pointer = getattr(context, "button_pointer", None)
    button_prop = getattr(context, "button_prop", None)
    button_operator = getattr(context, "button_operator", None)
    
    # Show if we can detect an operator or boolean property
    if button_operator or (button_prop and button_prop.type == 'BOOLEAN'):
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
