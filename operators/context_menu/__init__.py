"""Context menu operator and registration."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught

import bpy  # type: ignore
from bpy.props import BoolProperty, StringProperty, EnumProperty  # type: ignore

from ..common import prefs, schedule_autosave_safe
from .extractors import (
    extract_from_button_pointer,
    extract_context_path,
    detect_editor_context
)
from .suggester import suggest_chord
from ...core.contexts import (
    ALL_CONTEXT,
    CONTEXTS,
    CONTEXT_TOKENS,
    DEFAULT_CONTEXT,
    context_label,
    enum_items as _context_enum_items,
)
from ...utils.context_path import normalize_bpy_data_path

# ENUM_FLAG items (power-of-two values) so several contexts can be ticked
# at once in the "Add Chord Mapping" dialog.
_CONTEXT_FLAG_ENUM_ITEMS = _context_enum_items(include_all=False, icons=True, flags=True)
# Context toggles per row in the dialog (dialog is ~450 px wide).
_CONTEXT_GRID_COLUMNS = 3

def _group_search(_self, context, _edit_text):
    """Suggest existing group names; new names can still be typed freely."""
    try:
        return sorted(g.name for g in prefs(context).groups if g.name)
    except Exception:
        return []

class CHORDSONG_OT_ContextMenu(bpy.types.Operator):
    """Add a chord mapping for this UI element"""
    bl_idname = "chordsong.context_menu"
    bl_label = "Add Chord Mapping"
    bl_options = {"REGISTER", "UNDO"}

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
        description="Type of mapping (OPERATOR, CONTEXT_TOGGLE, or CONTEXT_PROPERTY)",
        default="OPERATOR",
    )

    property_value: StringProperty(
        name="Value",
        description="Value to set for the property",
        default="",
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
        search=_group_search,
    )

    icon: StringProperty(
        name="Icon",
        description="Nerd Fonts emoji/icon for this chord",
        default="",
    )

    editor_context: EnumProperty(
        name="Editor Context",
        description="Editor contexts where this chord mapping will be active (one mapping added per selected context)",
        items=_CONTEXT_FLAG_ENUM_ITEMS,
        options={'ENUM_FLAG'},
        default={DEFAULT_CONTEXT},
    )

    global_context: BoolProperty(
        name="Global",
        description="Add one chord active in every editor instead of one per selected context",
        default=False,
    )

    sub_operators_json: StringProperty(
        name="Sub-Operators",
        description="JSON string of additional operators for consecutive calls",
        default="",
    )

    sub_items_json: StringProperty(
        name="Sub-Items",
        description="JSON string of additional properties/toggles",
        default="",
    )

    def _invoke_dialog(self, context):
        """Helper method to invoke the dialog with window-level context.

        The editor the dialog was summoned from is pre-ticked on top of
        whatever the operator/property heuristics suggested — but only when
        that editor actually has a context. Editors without one (Properties,
        Outliner, File Browser, ...) detect as the 3D View default, and
        unioning that in would quietly add a second, unwanted 3D View copy
        of every chord made from their buttons.
        """
        try:
            from ...core.contexts import SUPPORTED_SPACE_TYPES
            from ..common import detect_editor_context as detect_area_context, editor_state
            (space_type, _tree, _mode), _hints = editor_state(context)
            if space_type in SUPPORTED_SPACE_TYPES:
                area_context = detect_area_context(context)
                if area_context in CONTEXT_TOKENS:
                    self.editor_context = set(self.editor_context) | {area_context}
        except Exception:
            pass
        window_manager = context.window_manager
        return window_manager.invoke_props_dialog(self, width=450)

    def invoke(self, context, event):
        """Extract operator or property info and show dialog."""
        try:
            # Reset all properties
            self.operator = ""
            self.kwargs = ""
            self.sub_operators_json = ""
            self.sub_items_json = ""
            self.context_path = ""
            self.property_value = ""
            self.mapping_type = "OPERATOR"
            self.chord = ""
            self.name = ""
            self.group = ""
            self.icon = ""
            self.editor_context = {DEFAULT_CONTEXT}
            self.global_context = False

            button_operator = getattr(context, "button_operator", None)
            button_prop = getattr(context, "button_prop", None)
            button_pointer = getattr(context, "button_pointer", None)

            # 0. Extract from button_operator directly if present
            if button_operator and not self.operator:
                # Try to get bl_idname (e.g. "mesh.primitive_monkey_add")
                if hasattr(button_operator, "bl_idname"):
                    self.operator = button_operator.bl_idname
                else:
                    # Fallback: parse from class name MESH_OT_primitive_monkey_add
                    tpname = button_operator.__class__.__name__
                    if "_OT_" in tpname:
                        parts = tpname.split("_OT_")
                        if len(parts) == 2:
                            self.operator = f"{parts[0].lower()}.{parts[1].lower()}"

            # 1. Try to extract from Info Panel / Clipboard if no button context
            if not button_operator and not self.operator and not button_prop:
                from .extractors import extract_multiple_from_info_panel
                results = extract_multiple_from_info_panel(context)
                
                if results:
                    import json
                    first = results[0]
                    
                    if first['type'] == 'OPERATOR':
                        self.operator = first['operator']
                        self.kwargs = first['kwargs']
                        self.mapping_type = "OPERATOR"
                        
                        # Store others as JSON
                        if len(results) > 1:
                            self.sub_operators_json = json.dumps(results[1:])
                    
                    elif first['type'] == 'PROPERTY':
                        # Path is already normalized by parse_property_from_text
                        self.context_path = first['path']
                        self.property_value = first['value']
                        
                        # Guess if it's a toggle
                        is_bool = self.property_value.lower() in ("true", "false")
                        self.mapping_type = "CONTEXT_TOGGLE" if is_bool else "CONTEXT_PROPERTY"
                        
                        # Format label/group
                        self.name = self.context_path.split(".")[-1].replace("_", " ").title()
                        self.group = "Toggle" if is_bool else "Property"
                        
                        # Store others as JSON
                        if len(results) > 1:
                            self.sub_items_json = json.dumps(results[1:])

            # 2. Try to extract from button pointer (e.g. search menu items with no button_operator)
            if not self.operator and not self.context_path and button_pointer:
                op_id, op_inst, op_kwargs = extract_from_button_pointer(button_pointer)
                if op_id:
                    self.operator = op_id
                    if op_kwargs:
                        self.kwargs = op_kwargs
                if op_inst:
                    button_operator = op_inst

            # 3. Check if it's a property (from UI interaction, not Info selection)
            if button_prop and button_pointer and not button_operator and not self.context_path:
                self.context_path = extract_context_path(button_prop, button_pointer, context=context)
                # Normalize bpy.data paths if present (should already be normalized, but ensure it)
                if self.context_path:
                    self.context_path = normalize_bpy_data_path(self.context_path)
                self.name = button_prop.name or button_prop.identifier.replace("_", " ").title()
                self.editor_context = {detect_editor_context(context, kwargs=self.kwargs)}

                if button_prop.type == 'BOOLEAN':
                    self.mapping_type = "CONTEXT_TOGGLE"
                    self.group = "Toggle"
                else:
                    self.mapping_type = "CONTEXT_PROPERTY"
                    self.group = "Property"
                    try:
                        # Try to get current value from button_pointer if possible
                        val = getattr(button_pointer, button_prop.identifier)
                        # Special handling for mathutils types
                        if hasattr(val, "to_tuple"):
                            val = val.to_tuple()
                        elif hasattr(val, "to_list"):
                            val = val.to_list()
                        self.property_value = repr(val)
                    except Exception:
                        self.property_value = ""

                self.chord = suggest_chord(self.group, self.name)
                return self._invoke_dialog(context)

            # 4. Process found operator
            if self.operator:
                # If we have an operator str but maybe no instance
                if "." in self.operator:
                    parts = self.operator.split(".")
                    if len(parts) == 2:
                        self.group = parts[0].replace("_", " ").title()
                        self.name = parts[1].replace("_", " ").title()

                self.editor_context = {detect_editor_context(context, self.operator, self.kwargs)}

                # Refine info if we have the button_operator instance
                if button_operator:
                    # Get nicely formatted name from class name if possible
                    tpname = button_operator.__class__.__name__
                    if "_OT_" in tpname:
                        parts = tpname.split("_OT_")
                        if len(parts) == 2:
                            self.group = parts[0].replace("_", " ").title()
                            self.name = parts[1].replace("_", " ").title()

                    # Extract args
                    args = []
                    node_type_value = None
                    try:
                        keys = button_operator.keys()
                        if keys:
                            for k in keys:
                                try:
                                    v = getattr(button_operator, k)
                                    # Special handling for node types
                                    if k == 'type' and isinstance(v, str) and self.operator.startswith("node."):
                                        node_type_value = v

                                    # Handle mathutils types (Vector, Color, Euler, etc.)
                                    if hasattr(v, "to_tuple"):
                                        v = v.to_tuple()
                                    elif hasattr(v, "to_list"):
                                        v = v.to_list()

                                    # Use repr to get a Python-evaluable string for the value
                                    val_str = repr(v)
                                    
                                    # Blender's repr for vectors/colors might include the class name, 
                                    # let's try to keep it simple if possible but repr is safest for round-trip
                                    args.append(f'{k} = {val_str}')
                                except Exception:
                                    continue
                    except Exception:
                        pass

                    if node_type_value:
                        import re
                        node_name = node_type_value
                        for prefix in ['ShaderNode', 'GeometryNode', 'CompositorNode', 'TextureNode']:
                            if node_name.startswith(prefix):
                                node_name = node_name[len(prefix):]
                                break
                        node_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', node_name)
                        node_name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', node_name)
                        self.name = node_name

                    if args:
                        self.kwargs = ", ".join(args)

                self.chord = suggest_chord(self.group, self.name)
                return self._invoke_dialog(context)

            # 5. Process found property (from Info selection)
            if self.context_path:
                self.editor_context = {detect_editor_context(context, kwargs=self.kwargs)}
                self.chord = suggest_chord(self.group, self.name)
                return self._invoke_dialog(context)

            # 6. Fallback: Show dialog for manual entry
            self.mapping_type = "OPERATOR"
            return self._invoke_dialog(context)

        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                return self._invoke_dialog(context)
            except Exception:
                self.report({'ERROR'}, f"Failed to show dialog: {e}")
                return {'CANCELLED'}

    def draw(self, context):
        """Draw the dialog UI"""
        layout = self.layout

        # Pick up icon chosen via the icon-select popup (no persistent target yet)
        from ..icon_select import consume_pending_dialog_icon
        pending_icon = consume_pending_dialog_icon()
        if pending_icon is not None:
            self.icon = pending_icon

        col = layout.column(align=True)
        if self.mapping_type in ("CONTEXT_TOGGLE", "CONTEXT_PROPERTY"):
            import json
            sub_count = 0
            if self.sub_items_json:
                try:
                    sub_count = len(json.loads(self.sub_items_json))
                except Exception:
                    pass
            
            # Use appropriate icon based on mapping type
            path_icon = "CHECKBOX_HLT" if self.mapping_type == "CONTEXT_TOGGLE" else "PROPERTIES"
            
            if sub_count > 0:
                col.label(text=f"Multiple {self.mapping_type.split('_')[-1].title()}s: {self.context_path} + {sub_count} more", icon=path_icon)
            else:
                col.label(text=f"Path: {self.context_path}", icon=path_icon)
        else:
            if self.operator:
                import json
                sub_count = 0
                if self.sub_operators_json:
                    try:
                        sub_count = len(json.loads(self.sub_operators_json))
                    except Exception:
                        pass
                
                if sub_count > 0:
                    col.label(text=f"Multiple Operators: {self.operator} + {sub_count} more", icon="SETTINGS")
                else:
                    col.label(text=f"Operator: {self.operator}", icon="SETTINGS")
            else:
                col.label(text="Operator not detected automatically", icon="INFO")
                col.label(text="Please enter the operator ID manually", icon="BLANK1")
                col.separator()
                col.label(text="Example: uv.weld", icon="BLANK1")
                col.label(text="(You can see the Python command in the search menu)", icon="BLANK1")
                col.separator()

        if not self.operator and self.mapping_type == "OPERATOR":
            col.label(text="Operator ID:", icon="SETTINGS")
            col.prop(self, "operator", text="")
            col.separator()

        col.label(text="Enter Chord:")
        col.prop(self, "chord", text="")
        col.separator()

        # Show mapping type indicator
        if self.mapping_type == "CONTEXT_TOGGLE":
            col.label(text="Type: Toggle", icon="CHECKBOX_HLT")
        elif self.mapping_type == "CONTEXT_PROPERTY":
            col.label(text="Type: Property", icon="PROPERTIES")
        col.separator()

        col.label(text="Editor Context:")
        col.prop(self, "global_context", text="Global (every editor)", icon="WORLD", toggle=True)
        # One toggle per editor, wrapped into a grid so 16 contexts fit the
        # dialog width; greyed out while Global is on.
        grid = col.grid_flow(row_major=True, columns=_CONTEXT_GRID_COLUMNS, even_columns=True, align=True)
        grid.enabled = not self.global_context
        for ctx in CONTEXTS:
            grid.prop_enum(self, "editor_context", ctx.token, icon=ctx.icon)
        col.separator()

        row = col.row(align=True)
        row.prop(self, "name", text="Label")
        icon_sub = row.row(align=True)
        icon_sub.scale_x = 0.6
        icon_sub.prop(self, "icon", text="Icon")
        op = row.operator("chordsong.icon_select", text="", icon="DOWNARROW_HLT")
        op.target_dialog = self.bl_idname
        op.target_prop = "icon"
        col.prop(self, "group", text="Group")
        if self.mapping_type == "CONTEXT_PROPERTY":
            col.prop(self, "property_value", text="Value")
        else:
            col.prop(self, "kwargs", text="Parameters")

    def execute(self, context: bpy.types.Context):
        p = prefs(context)

        # Never cancel here: Blender cannot disable a dialog's OK, and
        # cancelling discards the operator, label, group and parameters the
        # user just filled in. Create the mapping and say what is missing —
        # "Add New Chord" already creates chordless mappings the same way.
        if not self.chord:
            self.report({'WARNING'}, "No chord entered - set it in the Mappings tab")

        # One mapping is added per selected editor context, in registry order;
        # Global adds a single ALL mapping instead.
        if self.global_context:
            contexts = [ALL_CONTEXT]
        else:
            contexts = [c for c in CONTEXT_TOKENS if c in self.editor_context]
        if not contexts:
            from ..common import detect_editor_context as _detect
            contexts = [_detect(context)]
            self.report({'WARNING'}, "No context ticked - added to "
                        + context_label(contexts[0]))

        # Normalize context_path if it contains bpy.data or matches indexed collection pattern
        # This handles both manually entered paths and paths from Info panel
        if self.context_path:
            self.context_path = normalize_bpy_data_path(self.context_path)

        if self.mapping_type == "CONTEXT_TOGGLE":
            if not self.context_path:
                self.report({'WARNING'}, "No context path specified")
                return {"CANCELLED"}

            for ctx in contexts:
                m = p.mappings.add()
                m.enabled = True
                m.chord = self.chord
                m.label = self.name if self.name else "Toggle"
                m.group = self.group if self.group else ""
                m.icon = self.icon
                m.context = ctx
                m.context_path = self.context_path
                m.mapping_type = "CONTEXT_TOGGLE"

                # Handle additional items
                if self.sub_items_json:
                    try:
                        import json
                        subs = json.loads(self.sub_items_json)
                        for sub_data in subs:
                            if sub_data['type'] == 'PROPERTY':
                                sub = m.sub_items.add()
                                sub.path = sub_data['path']
                                sub.value = sub_data['value']
                    except Exception:
                        pass

            msg = f"Added chord '{self.chord}' for toggle: {self.context_path}"
        elif self.mapping_type == "CONTEXT_PROPERTY":
            if not self.context_path:
                self.report({'WARNING'}, "No context path specified")
                return {"CANCELLED"}

            for ctx in contexts:
                m = p.mappings.add()
                m.enabled = True
                m.chord = self.chord
                m.label = self.name if self.name else "Set Property"
                m.group = self.group if self.group else "Property"
                m.icon = self.icon
                m.context = ctx
                m.context_path = self.context_path
                m.property_value = self.property_value
                m.mapping_type = "CONTEXT_PROPERTY"

                # Handle additional items
                if self.sub_items_json:
                    try:
                        import json
                        subs = json.loads(self.sub_items_json)
                        for sub_data in subs:
                            if sub_data['type'] == 'PROPERTY':
                                sub = m.sub_items.add()
                                sub.path = sub_data['path']
                                sub.value = sub_data['value']
                    except Exception:
                        pass

            msg = f"Added chord '{self.chord}' to set {self.context_path} to {self.property_value}"
        else:
            if not self.operator:
                self.report({'WARNING'}, "No operator specified")
                return {"CANCELLED"}

            if not self.name or not self.group:
                # Guess from ID
                if "." in self.operator:
                    parts = self.operator.split(".")
                    if len(parts) == 2:
                        if not self.group:
                            self.group = parts[0].replace("_", " ").title()
                        if not self.name:
                            self.name = parts[1].replace("_", " ").title()

            for ctx in contexts:
                m = p.mappings.add()
                m.enabled = True
                m.chord = self.chord
                m.label = self.name if self.name else "New Chord"
                m.group = self.group if self.group else ""
                m.icon = self.icon
                m.context = ctx
                m.operator = self.operator
                m.call_context = "INVOKE_DEFAULT"
                m.kwargs_json = self.kwargs if self.kwargs else ""
                m.mapping_type = "OPERATOR"

                # Handle consecutive operators
                if self.sub_operators_json:
                    try:
                        import json
                        subs = json.loads(self.sub_operators_json)
                        for sub_data in subs:
                            if sub_data['type'] == 'OPERATOR':
                                sub = m.sub_operators.add()
                                sub.operator = sub_data['operator']
                                sub.kwargs_json = sub_data['kwargs']
                                sub.call_context = "EXEC_DEFAULT"
                    except Exception as e:
                        self.report({'WARNING'}, f"Failed to parse sub-operators: {e}")
                        print(f"Chord Song: Failed to parse sub-operators: {e}")

            msg = f"Added chord '{self.chord}' for: {self.operator}"

        # Move the newly added mappings to the top, preserving their order
        for _ in contexts:
            last_index = len(p.mappings) - 1
            if last_index > 0:
                p.mappings.move(last_index, 0)

        if len(contexts) > 1:
            msg += f" ({len(contexts)} contexts)"

        schedule_autosave_safe(p, delay_s=5.0)

        self.report({'INFO'}, msg)
        return {"FINISHED"}

def button_context_menu_draw(self, context):
    """Draw function that adds our button to the right-click context menu."""
    layout = self.layout
    layout.separator()
    # Force INVOKE_DEFAULT to ensure the dialog shows up, especially in Info/Console panels
    layout.operator_context = 'INVOKE_DEFAULT'
    layout.operator(CHORDSONG_OT_ContextMenu.bl_idname, text="Add Chord Mapping", icon="EVENT_C")

def register_context_menu():
    """Register the context menu hook using UI_MT_button_context_menu (modern Blender API)."""
    # Register to UI_MT_button_context_menu (works across all platforms including macOS)
    if hasattr(bpy.types, "UI_MT_button_context_menu"):
        try:
            bpy.types.UI_MT_button_context_menu.append(button_context_menu_draw)
        except Exception:
            pass
    
    # Also register to Info Editor context menu for Info panel compatibility
    if hasattr(bpy.types, "INFO_MT_context_menu"):
        try:
            bpy.types.INFO_MT_context_menu.append(button_context_menu_draw)
        except Exception:
            pass

def unregister_context_menu():
    """Unregister the context menu hook"""
    # Remove from UI_MT_button_context_menu
    if hasattr(bpy.types, "UI_MT_button_context_menu"):
        try:
            bpy.types.UI_MT_button_context_menu.remove(button_context_menu_draw)
        except Exception:
            pass

    # Remove from Info Editor context menu
    if hasattr(bpy.types, "INFO_MT_context_menu"):
        try:
            bpy.types.INFO_MT_context_menu.remove(button_context_menu_draw)
        except Exception:
            pass

__all__ = [
    "CHORDSONG_OT_ContextMenu",
    "register_context_menu",
    "unregister_context_menu"
]
