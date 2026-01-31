"""Operators for managing statistics."""

# pyright: reportMissingImports=false
# pylint: disable=import-error,broad-exception-caught

import json

import bpy
from bpy.types import Operator

from ..core.engine import chord_to_display_form
from ..utils.addon_package import addon_root_package
from .common import prefs, schedule_autosave_safe
from .context_menu.extractors import detect_editor_context, normalize_bpy_data_path
from .context_menu.suggester import suggest_chord


def _get_blacklist(prefs):
    """Get blacklist as a set of 'category:name' strings."""
    try:
        blacklist_json = prefs.stats_blacklist or "[]"
        return set(json.loads(blacklist_json))
    except Exception:
        return set()


def _save_blacklist(prefs, blacklist_set):
    """Save blacklist set as JSON string."""
    try:
        prefs.stats_blacklist = json.dumps(sorted(list(blacklist_set)))
    except Exception:
        pass


def _make_blacklist_key(category, name):
    """Create blacklist key from category and name."""
    return f"{category}:{name}"


def _write_stats_to_file(prefs):
    """
    Overwrite the stats file with current UI state (what is displayed).
    Uses the canonical stats path (export path if set, else internal).
    Returns True on success, False otherwise.
    """
    from ..core.stats_manager import ChordSong_StatsManager
    path = ChordSong_StatsManager.get_stats_file_path()
    return path and ChordSong_StatsManager.write_current_to_file(path)


class CHORDSONG_OT_Stats_Reload(Operator):
    """Reload statistics from the stats file (same file as Export/load)"""
    bl_idname = "chordsong.stats_reload"
    bl_label = "Reload from JSON"
    bl_description = "Reload statistics from the stats file; replaces in-memory data with file content"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        """Reload from the stats file (same file as Export/load) and refresh UI."""
        try:
            from ..core.stats_manager import ChordSong_StatsManager
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences
            path = ChordSong_StatsManager.get_stats_file_path()
            if ChordSong_StatsManager.reload_from_path(path):
                ChordSong_StatsManager.load_blacklist_from_path(path)
                _refresh_stats_ui(prefs, export_to_file=False)
                self.report({'INFO'}, "Statistics reloaded from JSON")
            else:
                self.report({'WARNING'}, "No stats file found or could not load")
        except Exception as e:
            self.report({'ERROR'}, f"Failed to reload: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


def _refresh_stats_ui(prefs, export_to_file=False):
    """
    Rebuild the stats UI list from get_stats() (optionally save to file after).
    prefs: addon preferences. export_to_file: if True, also write current state to stats file (e.g. Refresh button).
    Returns True on success, False on error.
    """
    try:
        from ..core.stats_manager import ChordSong_StatsManager

        # Clear the collection
        prefs.stats_collection.clear()

        # Get blacklist
        blacklist = _get_blacklist(prefs)

        # Collect from both categories, excluding blacklisted
        all_stats = []
        for category in ("operators", "chords"):
            stats = ChordSong_StatsManager.get_stats(category)
            for name, count in stats.items():
                # Skip if blacklisted
                blacklist_key = _make_blacklist_key(category, name)
                if blacklist_key not in blacklist:
                    all_stats.append((category, name, count))

        # Sort by count (descending) or name (ascending) based on sort mode
        if prefs.stats_sort_by_usage:
            sorted_items = sorted(all_stats, key=lambda x: (-x[2], x[0], x[1]))
        else:
            sorted_items = sorted(all_stats, key=lambda x: (x[0], x[1]))

        # Populate the collection
        for category, name, count in sorted_items:
            item = prefs.stats_collection.add()
            item.category = category
            item.name = name
            item.count = count

            # For chords, find the mapping to get group and label
            if category == 'chords':
                # Find mapping by chord string (normalize so grave/` and +grave/~ match)
                for mapping in prefs.mappings:
                    if chord_to_display_form((mapping.chord or "").strip()) == name:
                        item.group = mapping.group or ""
                        item.label = mapping.label or ""
                        break

        # Optionally overwrite stats file with current state (e.g. when Refresh is clicked)
        if export_to_file:
            try:
                _write_stats_to_file(prefs)
            except Exception:
                pass  # Silently fail, refresh still succeeds

        return True
    except Exception:
        return False


class CHORDSONG_OT_Stats_Refresh(Operator):
    """Refresh statistics display and export to file"""
    bl_idname = "chordsong.stats_refresh"
    bl_label = "Refresh Statistics"
    bl_description = "Refresh the statistics display and export to file"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        """Refresh the statistics display and export to file."""
        try:
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences

            if not _refresh_stats_ui(prefs, export_to_file=True):
                self.report({'ERROR'}, "Failed to refresh statistics")
                return {'CANCELLED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to refresh statistics: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class CHORDSONG_OT_Stats_Export(Operator):
    """Overwrite the stats JSON file with what is currently displayed in the UI"""
    bl_idname = "chordsong.stats_export"
    bl_label = "Export Statistics"
    bl_description = "Overwrite the stats file with current UI state (export path if set, else internal file)"
    bl_options = {'INTERNAL'}

    def execute(self, context):
        """Overwrite the stats file with current UI state."""
        try:
            from ..core.stats_manager import ChordSong_StatsManager
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences
            path = ChordSong_StatsManager.get_stats_file_path()
            if not path:
                self.report({'ERROR'}, "Cannot determine stats file path.")
                return {'CANCELLED'}
            if _write_stats_to_file(prefs):
                self.report({'INFO'}, f"Statistics saved to {path}")
            else:
                self.report({'ERROR'}, "Failed to write statistics to file.")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Failed to export statistics: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}


class CHORDSONG_OT_Stats_Blacklist(Operator):
    """Manage blacklist for statistics items"""
    bl_idname = "chordsong.stats_blacklist"
    bl_label = "Blacklist Manager"
    bl_description = "Manage blacklist: toggle items, view/edit blacklist, or clear all"
    bl_options = {'INTERNAL'}

    action: bpy.props.EnumProperty(
        name="Action",
        description="Action to perform",
        items=[
            ('TOGGLE', "Toggle", "Toggle blacklist status for an item"),
            ('EDIT', "Edit", "Open blacklist editor dialog"),
            ('REMOVE', "Remove", "Remove item from blacklist"),
            ('CLEAR', "Clear", "Clear all blacklisted items"),
        ],
        default='TOGGLE',
    )

    category: bpy.props.StringProperty(
        name="Category",
        description="Item category (operator, chord)",
        default="",
    )

    name: bpy.props.StringProperty(
        name="Name",
        description="Item name",
        default="",
    )

    def invoke(self, context, event):
        """Invoke handler - opens dialog for EDIT action."""
        if self.action == 'EDIT':
            return context.window_manager.invoke_props_dialog(self, width=500)
        return self.execute(context)

    def execute(self, context):
        """Execute the blacklist action."""
        try:
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences

            if self.action == 'TOGGLE':
                # Toggle blacklist for item
                if self.category and self.name:
                    # Use provided category/name
                    blacklist_key = _make_blacklist_key(self.category, self.name)
                else:
                    # Use selected item from collection
                    index = prefs.stats_collection_index
                    if index < 0 or index >= len(prefs.stats_collection):
                        self.report({'WARNING'}, "No item selected")
                        return {'CANCELLED'}
                    item = prefs.stats_collection[index]
                    blacklist_key = _make_blacklist_key(item.category, item.name)

                blacklist = _get_blacklist(prefs)
                if blacklist_key in blacklist:
                    blacklist.remove(blacklist_key)
                    action_msg = "removed from"
                else:
                    blacklist.add(blacklist_key)
                    action_msg = "added to"

                _save_blacklist(prefs, blacklist)
                # Save blacklist to statistics file immediately
                try:
                    from ..core.stats_manager import ChordSong_StatsManager
                    # Trigger a save to update the blacklist in the JSON file
                    # Mark as dirty so the next auto-save will include the updated blacklist
                    ChordSong_StatsManager.mark_dirty()
                except Exception:
                    pass
                # Light refresh - just update UI, no file export needed
                _refresh_stats_ui(prefs, export_to_file=False)
                self.report({'INFO'}, f"Item {action_msg} blacklist")

            elif self.action == 'REMOVE':
                # Remove specific item from blacklist
                if not self.category or not self.name:
                    self.report({'WARNING'}, "Category and name required")
                    return {'CANCELLED'}

                blacklist_key = _make_blacklist_key(self.category, self.name)
                blacklist = _get_blacklist(prefs)
                if blacklist_key in blacklist:
                    blacklist.remove(blacklist_key)
                    _save_blacklist(prefs, blacklist)
                    # Save blacklist to statistics file
                    try:
                        from ..core.stats_manager import ChordSong_StatsManager
                        ChordSong_StatsManager.mark_dirty()
                    except Exception:
                        pass
                    # Light refresh - just update UI, no file export needed
                    _refresh_stats_ui(prefs, export_to_file=False)
                    # Reopen editor dialog
                    bpy.ops.chordsong.stats_blacklist('INVOKE_DEFAULT', action='EDIT')

            elif self.action == 'CLEAR':
                # Clear all blacklisted items
                _save_blacklist(prefs, set())
                # Save blacklist to statistics file
                try:
                    from ..core.stats_manager import ChordSong_StatsManager
                    ChordSong_StatsManager.mark_dirty()
                except Exception:
                    pass
                # Light refresh - just update UI, no file export needed
                _refresh_stats_ui(prefs, export_to_file=False)
                self.report({'INFO'}, "Blacklist cleared")

            elif self.action == 'EDIT':
                # This is handled by draw() method for the dialog
                pass

        except Exception as e:
            self.report({'ERROR'}, f"Failed to manage blacklist: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}

    def draw(self, context):
        """Draw the blacklist editor UI (for EDIT action)."""
        try:
            prefs = context.preferences.addons[addon_root_package(__package__)].preferences
            blacklist = _get_blacklist(prefs)

            layout = self.layout
            box = layout.box()

            if not blacklist:
                row = box.row()
                row.label(text="No items in blacklist", icon='INFO')
                return

            row = box.row()
            row.label(text=f"Blacklisted Items ({len(blacklist)}):", icon='CHECKBOX_HLT')

            # Display blacklisted items
            for blacklist_key in sorted(blacklist):
                row = box.row(align=True)
                category, name = blacklist_key.split(':', 1) if ':' in blacklist_key else ('unknown', blacklist_key)

                # Type icon
                type_icon = {
                    'operator': 'SETTINGS',
                    'chord': 'EVENT_SPACE'
                }.get(category, 'DOT')
                row.label(text=category.capitalize(), icon=type_icon)
                row.separator()
                row.label(text=name)
                row.separator()

                # Remove button
                op = row.operator("chordsong.stats_blacklist", text="Remove", icon='X')
                op.action = 'REMOVE'
                op.category = category
                op.name = name

            # Clear all button
            row = box.row()
            row.scale_y = 1.3
            op = row.operator("chordsong.stats_blacklist", text="Clear All Blacklist", icon='TRASH')
            op.action = 'CLEAR'

        except Exception:
            layout.label(text="Error loading blacklist", icon='ERROR')

    def cancel(self, context):
        """Called when dialog is cancelled."""
        pass


class CHORDSONG_OT_Stats_Convert_To_Chord(Operator):
    """Convert operator to a chord mapping"""
    bl_idname = "chordsong.stats_convert_to_chord"
    bl_label = "Convert to Chord"
    bl_description = "Create a new chord mapping for this operator"
    bl_options = {'INTERNAL'}

    category: bpy.props.StringProperty()  # Category from statistics ('operators' or 'chords')
    stats_name: bpy.props.StringProperty()  # Name from statistics (to avoid conflict with 'name' property)

    # Properties from context_menu (copied for compatibility)
    operator: bpy.props.StringProperty(default="")
    kwargs: bpy.props.StringProperty(default="")
    context_path: bpy.props.StringProperty(default="")
    mapping_type: bpy.props.StringProperty(default="OPERATOR")
    property_value: bpy.props.StringProperty(default="")
    chord: bpy.props.StringProperty(default="")
    name: bpy.props.StringProperty(default="")
    group: bpy.props.StringProperty(default="")
    editor_context: bpy.props.EnumProperty(
        name="Editor Context",
        items=(
            ("VIEW_3D", "3D View (Object)", "Active in 3D View (Object Mode)", "OBJECT_DATAMODE", 0),
            ("VIEW_3D_EDIT", "3D View (Edit)", "Active in 3D View (Edit Modes)", "EDITMODE_HLT", 1),
            ("GEOMETRY_NODE", "Geometry Nodes", "Active in Geometry Nodes editor", "GEOMETRY_NODES", 2),
            ("SHADER_EDITOR", "Shader Editor", "Active in Shader Editor", "NODE_MATERIAL", 3),
            ("IMAGE_EDITOR", "UV Editor", "Active in UV Editor", "IMAGE_COL", 4),
        ),
        default="VIEW_3D",
    )
    sub_operators_json: bpy.props.StringProperty(default="")
    sub_items_json: bpy.props.StringProperty(default="")

    def _invoke_dialog(self, context):
        """Helper method to invoke the dialog with window-level context."""
        window_manager = context.window_manager
        return window_manager.invoke_props_dialog(self, width=450)

    def _construct_operator_path(self, operator_name):
        """
        Construct full operator path from operator name.
        
        Handles two formats:
        1. Class name format: "TRANSFORM_OT_translate" -> "bpy.ops.transform.translate"
        2. bl_idname format: "transform.translate" -> "bpy.ops.transform.translate"
        
        Args:
            operator_name: Operator identifier (class name or bl_idname)
            
        Returns:
            Tuple of (full_operator_path, kwargs_string, button_operator_instance)
        """
        print(f"[DEBUG] _construct_operator_path: Input operator_name = '{operator_name}'")
        
        kwargs = ""
        button_operator = None
        
        # Determine operator path based on format
        if not operator_name:
            print("[DEBUG] _construct_operator_path: Empty operator_name, returning empty")
            return "", button_operator, kwargs
        
        if "_OT_" in operator_name and "." not in operator_name:
            # Split: "TRANSFORM_OT_translate" -> ("TRANSFORM", "translate")
            parts = operator_name.split("_OT_", 1)
            if len(parts) == 2:
                module = parts[0].lower()
                op_name = parts[1].lower()
                operator_path = f"bpy.ops.{module}.{op_name}"
                print(f"[DEBUG] _construct_operator_path: Pattern 1 (class name) -> operator_path = '{operator_path}'")
                
                # Try to get operator class to extract kwargs if not in metadata
                if not kwargs:
                    try:
                        op_class = getattr(bpy.types, operator_name, None)
                        if op_class and issubclass(op_class, bpy.types.Operator):
                            try:
                                button_operator = op_class()
                                kwargs = self._extract_kwargs_from_operator(button_operator)
                                print(f"[DEBUG] _construct_operator_path: Found operator class, kwargs = '{kwargs}'")
                            except Exception as e:
                                print(f"[DEBUG] _construct_operator_path: Failed to instantiate operator class: {e}")
                        else:
                            print(f"[DEBUG] _construct_operator_path: Operator class not found or not an Operator: {op_class}")
                    except Exception as e:
                        print(f"[DEBUG] _construct_operator_path: Exception getting operator class: {e}")
                
                print(f"[DEBUG] _construct_operator_path: Returning ({operator_path}, {button_operator}, '{kwargs}')")
                return operator_path, button_operator, kwargs
        
        # Pattern 2: bl_idname format (e.g., "transform.translate")
        if "." in operator_name:
            # Check if it already has "bpy.ops." prefix
            if operator_name.startswith("bpy.ops."):
                operator_path = operator_name
            else:
                # Add "bpy.ops." prefix: "transform.translate" -> "bpy.ops.transform.translate"
                operator_path = f"bpy.ops.{operator_name}"
            print(f"[DEBUG] _construct_operator_path: Pattern 2 (bl_idname) -> operator_path = '{operator_path}'")
            
            # Try to extract kwargs if not in metadata
            if not kwargs:
                try:
                    module_name, op_name = operator_name.split(".", 1)
                    # Try to get operator class: "transform.translate" -> "TRANSFORM_OT_translate"
                    op_class_name = f"{module_name.upper()}_OT_{op_name}"
                    print(f"[DEBUG] _construct_operator_path: Trying to get operator class '{op_class_name}'")
                    op_class = getattr(bpy.types, op_class_name, None)
                    if op_class and issubclass(op_class, bpy.types.Operator):
                        try:
                            button_operator = op_class()
                            kwargs = self._extract_kwargs_from_operator(button_operator)
                            print(f"[DEBUG] _construct_operator_path: Found operator class, kwargs = '{kwargs}'")
                        except Exception as e:
                            print(f"[DEBUG] _construct_operator_path: Failed to instantiate operator class: {e}")
                    else:
                        print(f"[DEBUG] _construct_operator_path: Operator class not found or not an Operator: {op_class}")
                except Exception as e:
                    print(f"[DEBUG] _construct_operator_path: Exception extracting kwargs: {e}")
            
            print(f"[DEBUG] _construct_operator_path: Returning ({operator_path}, {button_operator}, '{kwargs}')")
            return operator_path, button_operator, kwargs
        
        # Fallback: return as-is (might be invalid, but let user fix it)
        print(f"[DEBUG] _construct_operator_path: Fallback -> returning operator_name as-is: '{operator_name}'")
        return operator_name, button_operator, kwargs
    
    def _extract_kwargs_from_operator(self, button_operator):
        """Extract kwargs string from operator instance."""
        args = []
        try:
            keys = button_operator.keys()
            if keys:
                for k in keys:
                    try:
                        v = getattr(button_operator, k)
                        # Skip internal properties
                        if k.startswith('_') or k in ('bl_idname', 'bl_label', 'bl_options', 'bl_property'):
                            continue
                        
                        # Handle mathutils types
                        if hasattr(v, "to_tuple"):
                            v = v.to_tuple()
                        elif hasattr(v, "to_list"):
                            v = v.to_list()
                        
                        # Use repr to get a Python-evaluable string
                        val_str = repr(v)
                        args.append(f'{k} = {val_str}')
                    except Exception:
                        continue
        except Exception:
            pass
        
        return ", ".join(args) if args else ""

    def invoke(self, context, event):
        """Extract operator or property info from name and show dialog."""
        print(f"[DEBUG] invoke: Called with category='{self.category}', stats_name='{self.stats_name}'")
        try:
            # Reset all properties (inherited from parent)
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
            self.editor_context = "VIEW_3D"

            # Debug: Check what we received
            if not self.stats_name:
                print("[DEBUG] invoke: No stats_name provided")
                self.report({'WARNING'}, "No operator/property name provided")
                return self._invoke_dialog(context)

            # Extract from operator name (instead of button context)
            # Note: category is 'operators' (plural) from stats, not 'operator' (singular)
            if self.category == 'operators':
                # Construct full operator path (e.g., "bpy.ops.transform.translate")
                operator_path, button_operator, kwargs = self._construct_operator_path(self.stats_name)

                if not operator_path:
                    # If construction failed, try to construct from stats_name
                    if "." in self.stats_name:
                        operator_path = f"bpy.ops.{self.stats_name}"
                    else:
                        operator_path = self.stats_name
                    print(f"[DEBUG] invoke: Construction failed, using fallback operator_path = '{operator_path}'")

                print(f"[DEBUG] invoke: Final constructed operator_path = '{operator_path}'")
                print(f"[DEBUG] invoke: Final kwargs = '{kwargs}'")
                print(f"[DEBUG] invoke: button_operator = {button_operator}")

                self.operator = operator_path
                self.kwargs = kwargs
                self.mapping_type = "OPERATOR"

                # Extract group and name from operator path
                # Remove "bpy.ops." prefix if present
                op_name_for_display = operator_path.replace("bpy.ops.", "")
                if "." in op_name_for_display:
                    parts = op_name_for_display.split(".", 1)
                    if len(parts) == 2:
                        self.group = parts[0].replace("_", " ").title()
                        self.name = parts[1].replace("_", " ").title()

                # Refine info if we have the button_operator instance
                if button_operator:
                    # Get nicely formatted name from class name
                    tpname = button_operator.__class__.__name__
                    if "_OT_" in tpname:
                        parts = tpname.split("_OT_")
                        if len(parts) == 2:
                            self.group = parts[0].replace("_", " ").title()
                            self.name = parts[1].replace("_", " ").title()

                    # Special handling for node operators
                    node_type_value = None
                    try:
                        keys = button_operator.keys()
                        if keys:
                            for k in keys:
                                try:
                                    v = getattr(button_operator, k)
                                    if k == 'type' and isinstance(v, str) and self.operator.startswith("node."):
                                        node_type_value = v
                                        break
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

                # Detect editor context
                self.editor_context = detect_editor_context(context, self.operator, self.kwargs)

                # Suggest chord
                self.chord = suggest_chord(self.group, self.name)

                return self._invoke_dialog(context)


            # Fallback: Show dialog for manual entry
            print(f"[DEBUG] invoke: Unknown category '{self.category}', showing dialog for manual entry")
            self.mapping_type = "OPERATOR"
            self.operator = self.stats_name  # At least set the operator name
            return self._invoke_dialog(context)

        except Exception as exc:
            import traceback
            traceback.print_exc()
            # Even on error, show dialog with what we have
            try:
                if not self.operator and self.stats_name:
                    self.operator = self.stats_name
                return self._invoke_dialog(context)
            except Exception:
                self.report({'ERROR'}, f"Failed to show dialog: {exc}")
                return {'CANCELLED'}

    def draw(self, context):
        """Draw the dialog UI - copied from context_menu."""
        layout = self.layout

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
            path_icon = "PROPERTIES"

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
        row = col.row(align=True)
        row.prop(self, "editor_context", expand=True)
        col.separator()

        col.prop(self, "name", text="Label")
        col.prop(self, "group", text="Group")
        if self.mapping_type == "CONTEXT_PROPERTY":
            col.prop(self, "property_value", text="Value")
        else:
            col.prop(self, "kwargs", text="Parameters")

    def execute(self, context):
        """Create the mapping - copied from context_menu with tab switch."""
        p = prefs(context)

        if not self.chord:
            self.report({'WARNING'}, "Please enter a chord")
            return {"CANCELLED"}

        # Normalize context_path if it contains bpy.data or matches indexed collection pattern
        if self.context_path:
            self.context_path = normalize_bpy_data_path(self.context_path)

        if self.mapping_type == "CONTEXT_TOGGLE":
            if not self.context_path:
                self.report({'WARNING'}, "No context path specified")
                return {"CANCELLED"}

            m = p.mappings.add()
            m.enabled = True
            m.chord = self.chord
            m.label = self.name if self.name else "Toggle"
            m.group = self.group if self.group else ""
            m.context = self.editor_context
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

            m = p.mappings.add()
            m.enabled = True
            m.chord = self.chord
            m.label = self.name if self.name else "Set Property"
            m.group = self.group if self.group else "Property"
            m.context = self.editor_context
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
                    print(f"Chord Song: Failed to parse sub-operators: {e}")

            msg = f"Added chord '{self.chord}' for: {self.operator}"

        last_index = len(p.mappings) - 1
        if last_index > 0:
            p.mappings.move(last_index, 0)

        schedule_autosave_safe(p, delay_s=5.0)

        # Switch to mappings tab
        p.prefs_tab = "MAPPINGS"

        self.report({'INFO'}, msg)
        return {"FINISHED"}
