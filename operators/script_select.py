"""Script select operator with searchable list panel."""

# pyright: reportMissingImports=false
# pyright: reportMissingModuleSource=false
# pylint: disable=import-error,broad-exception-caught,invalid-name,import-outside-toplevel

import os
import bpy
from bpy.props import IntProperty, StringProperty

from .common import prefs

def fuzzy_match(query: str, text: str) -> tuple[bool, int]:
    """
    Fuzzy match query against text.
    Returns (matched, score) where lower score is better.
    Score is based on character positions and gaps.
    Treats underscores as spaces for easier matching.
    """
    if not query:
        return True, 0

    # Normalize: lowercase and treat underscores as spaces
    query = query.lower().replace('_', ' ')
    text = text.lower().replace('_', ' ')

    # Quick substring check for exact matches (best score)
    if query in text:
        return True, text.index(query) * 10

    # Fuzzy match: check if all query chars appear in order
    # Skip spaces in query for better matching (e.g., "my test" matches "mytest" or "my_test")
    query_chars = [c for c in query if c != ' ']

    query_idx = 0
    text_idx = 0
    last_match_idx = -1
    score = 0

    while query_idx < len(query_chars) and text_idx < len(text):
        # Skip spaces in text
        if text[text_idx] == ' ':
            text_idx += 1
            continue

        if query_chars[query_idx] == text[text_idx]:
            # Calculate gap penalty
            if last_match_idx >= 0:
                gap = text_idx - last_match_idx - 1
                score += gap * 5  # Penalize gaps
            score += text_idx  # Penalize later matches
            last_match_idx = text_idx
            query_idx += 1
        text_idx += 1

    # If we matched all query characters, it's a match
    if query_idx == len(query_chars):
        return True, score

    return False, float('inf')

class CHORDSONG_OT_Script_Select(bpy.types.Operator):
    """Select a Python script from the configured scripts folder."""

    bl_idname = "chordsong.script_select"
    bl_label = "Select Script"
    bl_options = {"REGISTER", "UNDO", "INTERNAL"}

    mapping_index: IntProperty(
        name="Mapping Index",
        description="Index of the mapping to update",
        default=-1,
    )

    search_filter: StringProperty(
        name="Search",
        description="Filter scripts by filename",
        default="",
    )

    def invoke(self, context, _event):
        """Show list popup dialog."""
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        """Draw list of scripts."""
        layout = self.layout
        p = prefs(context)

        # Check if scripts folder is configured
        scripts_folder = getattr(p, "scripts_folder", "")
        if not scripts_folder or not os.path.isdir(scripts_folder):
            layout.label(text="Scripts folder not configured or doesn't exist", icon="ERROR")
            layout.label(text="Please set the Scripts Folder in the Config section")
            return

        # Search box
        layout.prop(self, "search_filter", text="", icon="VIEWZOOM")
        layout.separator()

        # Get all .py files from the folder
        try:
            files = []
            for filename in os.listdir(scripts_folder):
                if filename.endswith(".py"):
                    full_path = os.path.join(scripts_folder, filename)
                    if os.path.isfile(full_path):
                        files.append((filename, full_path))

            # Fuzzy filter and sort by match score
            if self.search_filter:
                matched_files = []
                for filename, full_path in files:
                    matched, score = fuzzy_match(self.search_filter, filename)
                    if matched:
                        matched_files.append((filename, full_path, score))
                # Sort by score (lower is better), then by filename
                matched_files.sort(key=lambda x: (x[2], x[0].lower()))
                files = [(f[0], f[1]) for f in matched_files]
            else:
                # No search filter - sort alphabetically
                files.sort(key=lambda x: x[0].lower())

            if not files:
                if self.search_filter:
                    layout.label(text=f"No scripts found matching '{self.search_filter}'", icon="INFO")
                else:
                    layout.label(text="No Python scripts found in folder", icon="INFO")
                return

            # Display scripts in a scrollable box
            box = layout.box()
            col = box.column(align=True)

            for filename, full_path in files:
                row = col.row(align=True)
                op = row.operator(
                    "chordsong.script_select_apply",
                    text=filename,
                    icon="FILE_SCRIPT",
                    emboss=True,
                )
                op.script_path = full_path
                op.mapping_index = self.mapping_index

        except Exception as e:
            layout.label(text=f"Error reading scripts folder: {str(e)}", icon="ERROR")

    def execute(self, context):
        """Execute is called when dialog is confirmed, but we handle selection in apply operator."""
        return {"FINISHED"}

class CHORDSONG_OT_Script_Select_Apply(bpy.types.Operator):
    """Apply selected script to mapping."""

    bl_idname = "chordsong.script_select_apply"
    bl_label = "Apply Script"
    bl_options = {"INTERNAL"}

    script_path: StringProperty(default="")
    mapping_index: IntProperty(default=-1)

    def execute(self, context):
        """Apply the selected script."""
        p = prefs(context)

        if self.mapping_index < 0 or self.mapping_index >= len(p.mappings):
            self.report({"WARNING"}, "Invalid mapping index")
            return {"CANCELLED"}

        if not self.script_path:
            self.report({"WARNING"}, "No script path provided")
            return {"CANCELLED"}

        # Apply the script path
        mapping = p.mappings[self.mapping_index]
        mapping.python_file = self.script_path

        # Set the label to the script name (without .py extension)
        script_name = os.path.basename(self.script_path)
        if script_name.endswith(".py"):
            script_name = script_name[:-3]

        # Only set label if it's empty or generic
        if not mapping.label or mapping.label in ("New Chord", "(missing label)"):
            mapping.label = script_name

        from .common import schedule_autosave_safe
        schedule_autosave_safe(p, delay_s=5.0)

        # Close the dialog and redraw
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'PROPERTIES':
                    area.tag_redraw()

        return {"FINISHED"}
