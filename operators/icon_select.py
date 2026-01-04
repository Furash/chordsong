"""Icon select operator with grid-based popup panel."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import bpy
from bpy.props import IntProperty, StringProperty

from .common import prefs

class CHORDSONG_OT_Icon_Select(bpy.types.Operator):
    """Select an icon from Nerd Fonts library."""

    bl_idname = "chordsong.icon_select"
    bl_label = "Select Icon"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    mapping_index: IntProperty(
        name="Mapping Index",
        description="Index of the mapping to update",
        default=-1,
    )

    search_filter: StringProperty(
        name="Search",
        description="Filter icons by name",
        default="",
    )

    def invoke(self, context, _event):
        """Show grid popup dialog."""
        return context.window_manager.invoke_props_dialog(self, width=600)

    def draw(self, context):
        """Draw grid of icons."""
        layout = self.layout
        p = prefs(context)

        # Search box
        layout.prop(self, "search_filter", text="", icon="VIEWZOOM")
        layout.separator()

        # Grid layout
        grid = layout.grid_flow(row_major=True, columns=4, even_columns=True, even_rows=True, align=True)

        search_lower = self.search_filter.lower()

        # Create sorted list of (original_index, icon_item) tuples
        icon_list = [(idx, icon_item) for idx, icon_item in enumerate(p.nerd_icons)]
        icon_list.sort(key=lambda x: x[1].name.lower())

        for idx, icon_item in icon_list:
            # Filter by search
            if search_lower and search_lower not in icon_item.name.lower():
                continue

            # Create button for each icon
            col = grid.column(align=True)
            op = col.operator(
                "chordsong.icon_select_apply",
                text=icon_item.name,
                emboss=True,
            )
            op.icon_index = idx
            op.mapping_index = self.mapping_index

            # Show icon character below (will be gibberish but shows something)
            sub = col.row()
            sub.scale_y = 0.8
            sub.alignment = 'CENTER'
            sub.label(text=icon_item.icon)

    def execute(self, context):
        """Execute is called when dialog is confirmed, but we handle selection in apply operator."""
        return {"FINISHED"}

class CHORDSONG_OT_Icon_Select_Apply(bpy.types.Operator):
    """Apply selected icon to mapping."""

    bl_idname = "chordsong.icon_select_apply"
    bl_label = "Apply Icon"
    bl_options = {"INTERNAL"}

    icon_index: IntProperty(default=-1)
    mapping_index: IntProperty(default=-1)

    def execute(self, context):
        """Apply the selected icon."""
        p = prefs(context)

        if self.mapping_index < 0 or self.mapping_index >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        if self.icon_index < 0 or self.icon_index >= len(p.nerd_icons):
            self.report({"WARNING"}, "Invalid icon index")
            return {"CANCELLED"}

        # Apply the icon
        icon_char = p.nerd_icons[self.icon_index].icon
        mapping = p.mappings[self.mapping_index]
        mapping.icon = icon_char

        from .common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        # Close the dialog and redraw - wrap in try-except for safety
        try:
            for window in context.window_manager.windows:
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

        return {"FINISHED"}
