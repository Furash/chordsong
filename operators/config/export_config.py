"""Export config operator with selective export."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,attribute-defined-outside-init,invalid-name

import json
import os

import bpy  # type: ignore
from bpy.types import PropertyGroup  # type: ignore
from bpy.props import BoolProperty, CollectionProperty, StringProperty  # type: ignore
from bpy_extras.io_utils import ExportHelper  # type: ignore

from ...core.config_io import dump_prefs_filtered
from ..common import prefs


class CHORDSONG_PG_GroupSelection(PropertyGroup):
    """Property group for group selection checkbox."""
    name: StringProperty(name="Group Name")
    selected: BoolProperty(name="Selected", default=True)


class CHORDSONG_OT_Export_Config(bpy.types.Operator, ExportHelper):
    """Export chord mappings to a JSON config file with selective export."""

    bl_idname = "chordsong.export_config"
    bl_label = "Export Config"

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    # Class variable to store the active operator instance
    _active_instance = None

    # Group selections (dynamic)
    group_selections: CollectionProperty(type=CHORDSONG_PG_GroupSelection)

    # Helper property for select all/deselect all
    select_all_groups: BoolProperty(
        default=True,
        options={"HIDDEN"},
    )

    def _update_all_group_selections(self):
        """Update all group selections based on select_all_groups."""
        for item in self.group_selections:
            item.selected = self.select_all_groups

    # Flag to track if we've shown the selection dialog
    selections_confirmed: BoolProperty(
        default=False,
        options={"HIDDEN"},
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        """Show selection dialog first, then file browser."""
        # If selections are already confirmed, show file browser
        if self.selections_confirmed:
            # Default to extension-specific user directory
            try:
                # Use extension_path_user for extension-specific user directory
                extension_dir = bpy.utils.extension_path_user(__package__, path="", create=True)
                if extension_dir:
                    current_filepath = getattr(self, "filepath", "")
                    if not current_filepath or current_filepath.endswith("chordsong_export.json"):
                        self.filepath = os.path.join(extension_dir, "chordsong_export.json")
                else:
                    current_filepath = getattr(self, "filepath", "")
                    if not current_filepath:
                        self.filepath = os.path.join(os.path.expanduser("~"), "chordsong_export.json")
            except Exception:
                # Fallback to user_resource if extension_path_user is not available
                try:
                    presets_dir = bpy.utils.user_resource("SCRIPTS", path="presets", create=True)
                    if presets_dir:
                        folder = os.path.join(presets_dir, "chordsong")
                        os.makedirs(folder, exist_ok=True)
                        current_filepath = getattr(self, "filepath", "")
                        if not current_filepath or current_filepath.endswith("chordsong_export.json"):
                            self.filepath = os.path.join(folder, "chordsong_export.json")
                    else:
                        current_filepath = getattr(self, "filepath", "")
                        if not current_filepath:
                            self.filepath = os.path.join(os.path.expanduser("~"), "chordsong_export.json")
                except Exception:
                    current_filepath = getattr(self, "filepath", "")
                    if not current_filepath:
                        self.filepath = os.path.join(os.path.expanduser("~"), "chordsong_export.json")
            return super().invoke(context, event)

        # First time: show selection dialog
        p = prefs(context)

        # Initialize group selections
        self.group_selections.clear()
        group_names = set()

        # Collect all group names from groups collection
        for grp in p.groups:
            group_name = (getattr(grp, "name", "") or "").strip()
            if group_name:
                group_names.add(group_name)

        # Also collect group names from mappings (for "Ungrouped" handling)
        for m in p.mappings:
            group_name = (getattr(m, "group", "") or "").strip()
            if group_name:
                group_names.add(group_name)

        # Create selection entries for each group
        for group_name in sorted(group_names):
            item = self.group_selections.add()
            item.name = group_name
            item.selected = True  # Default to selected

        # Initialize select_all_groups property
        self.select_all_groups = True
        self.selections_confirmed = False

        # Store reference to this operator instance in class variable for toggle access
        CHORDSONG_OT_Export_Config._active_instance = self

        # Calculate width based on number of columns needed
        total_items = len(self.group_selections)
        num_columns = (total_items + 19) // 20  # Ceiling division
        dialog_width = 500 if num_columns == 1 else 800

        return context.window_manager.invoke_props_dialog(self, width=dialog_width)

    def draw(self, context: bpy.types.Context):
        """Draw the export selection dialog."""
        layout = self.layout

        # Header
        layout.label(text="Select Groups to Export", icon="EXPORT")

        # Select All / Deselect All buttons at the top
        btn_row = layout.row(align=True)
        # Check if all items are selected to determine button text
        all_selected = (
            all(item.selected for item in self.group_selections) if self.group_selections else True
        )
        # Create operator buttons for select/deselect
        if all_selected:
            op = btn_row.operator("chordsong.export_config_toggle_groups", text="Deselect All", emboss=True)
            op.toggle_to = False
        else:
            op = btn_row.operator("chordsong.export_config_toggle_groups", text="Select All", emboss=True)
            op.toggle_to = True

        # Groups section
        box = layout.box()
        header = box.row()
        header.label(text="Groups:", icon="FILE_FOLDER")

        # Group checkboxes with context hints
        if self.group_selections:
            p = prefs(context)
            # Build context map for each group
            group_contexts = {}
            for m in p.mappings:
                group_name = (getattr(m, "group", "") or "").strip()
                context = getattr(m, "context", "VIEW_3D")
                if group_name:
                    if group_name not in group_contexts:
                        group_contexts[group_name] = set()
                    group_contexts[group_name].add(context)

            # Split into columns with max 20 items per column
            items_per_column = 20
            total_items = len(self.group_selections)
            num_columns = (total_items + items_per_column - 1) // items_per_column  # Ceiling division

            # Create columns side by side
            columns_row = box.row()
            for col_idx in range(num_columns):
                col = columns_row.column()
                start_idx = col_idx * items_per_column
                end_idx = min(start_idx + items_per_column, total_items)

                # Add items to this column
                for i in range(start_idx, end_idx):
                    item = self.group_selections[i]
                    row = col.row(align=True)
                    row.prop(item, "selected", text="")

                    # Show context icons before group name
                    contexts = group_contexts.get(item.name, set())
                    if contexts:
                        # Map contexts to Blender icon names
                        context_icons = {
                            "ALL": "WORLD",
                            "VIEW_3D": "OBJECT_DATAMODE",
                            "VIEW_3D_EDIT": "EDITMODE_HLT",
                            "GEOMETRY_NODE": "GEOMETRY_NODES",
                            "SHADER_EDITOR": "SHADING_RENDERED",
                            "IMAGE_EDITOR": "UV",
                        }
                        for ctx in sorted(contexts):
                            icon_name = context_icons.get(ctx, "BLANK1")
                            row.label(text="", icon=icon_name)

                    # Group name
                    row.label(text=item.name)
        else:
            box.label(text="No groups found", icon="INFO")

    def execute(self, context: bpy.types.Context):
        """Export config to file with selected items."""
        # If selections not confirmed yet, confirm them and show file browser
        if not self.selections_confirmed:
            self.selections_confirmed = True
            # Re-invoke to show file browser
            # Use context's event if available, otherwise create minimal event object
            event = getattr(context, 'event', None)
            if event is None:
                class DummyEvent:
                    type = 'NONE'
                    value = 'PRESS'
                event = DummyEvent()
            return self.invoke(context, event)

        # File browser was shown and user selected a file, now export
        p = prefs(context)
        try:
            # Collect selected group names
            selected_groups = {item.name for item in self.group_selections if item.selected}

            # Build filter options - exclude leader_key
            # Always export mappings, groups, overlay, and scripts_folder
            filter_options = {
                "mappings": True,  # Always export mappings (no option to disable)
                "groups": True,  # Always export groups (they're part of mappings)
                "overlay": True,  # Always export overlay settings
                "scripts_folder": True,  # Always export scripts folder (it's a setting)
                "leader_key": False,  # Don't export leader key
                "selected_group_names": selected_groups,
            }

            data = dump_prefs_filtered(p, filter_options)
            text = json.dumps(data, indent=4, ensure_ascii=False)
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(text)
                f.write("\n")

            self.report({"INFO"}, f"Config exported to {os.path.basename(self.filepath)}")
            return {"FINISHED"}
        except Exception as ex:
            self.report({"ERROR"}, f"Failed to export config: {ex}")
            return {"CANCELLED"}
        finally:
            # Clean up reference and reset flag
            if CHORDSONG_OT_Export_Config._active_instance is self:
                CHORDSONG_OT_Export_Config._active_instance = None
            self.selections_confirmed = False


class CHORDSONG_OT_Export_Config_Toggle_Groups(bpy.types.Operator):
    """Toggle all selections (categories and groups) in export dialog."""

    bl_idname = "chordsong.export_config_toggle_groups"
    bl_label = "Toggle All Selections"
    bl_options = {"INTERNAL"}

    toggle_to: BoolProperty(default=True)

    def execute(self, context: bpy.types.Context):
        """Toggle all selections (categories and groups)."""
        # Access the export operator from class variable
        export_op = CHORDSONG_OT_Export_Config._active_instance

        if export_op:
            # Toggle all group selections
            if hasattr(export_op, 'group_selections'):
                for item in export_op.group_selections:
                    item.selected = self.toggle_to
                export_op.select_all_groups = self.toggle_to

            # Force redraw - wrap in try-except for safety
            try:
                if context.screen:
                    for area in context.screen.areas:
                        try:
                            area.tag_redraw()
                        except Exception:
                            pass
            except Exception:
                pass

        return {"FINISHED"}
