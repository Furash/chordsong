"""
Mappings tab for addon preferences.
"""

from ...core.engine import get_str_attr
from .mapping_item import draw_mapping_item, _is_mapping_conflicted

def draw_mappings_tab(prefs, context, layout):
    """Draw the Mappings tab content."""
    col = layout.column()

    # Leader Key section
    # Check user keyconfig first (contains user customizations), then addon keyconfig
    wm = context.window_manager
    keyconfigs = [wm.keyconfigs.user, wm.keyconfigs.addon]
    
    leader_box = col.box()

    # Header
    header_row = leader_box.row()
    header_row.alignment = 'CENTER'
    header_row.label(text="Leader Key Bindings:", icon='KEYINGSET')
    leader_box.separator()

    # Display all 3 keymaps
    keymap_configs = [
        ('3D View', '3D View'),
        ('Node Editor', 'Node Editor | Geometry Nodes'),
        ('Image', 'Image Editor | UV Editor'),
    ]

    for km_name, display_name in keymap_configs:
        # Check both keyconfigs to find the keymap item
        found_kmi = None
        found_km = None
        
        for kc in keyconfigs:
            if not kc:
                continue
            km = kc.keymaps.get(km_name)
            if km:
                for item in km.keymap_items:
                    if item.idname == "chordsong.leader":
                        found_kmi = item
                        found_km = km
                        break
            if found_kmi:
                break
        
        if found_kmi and found_km:
            row = leader_box.row(align=True)
            row.scale_y = 1.5
            row.label(text=f"{display_name}:")
            row.context_pointer_set("keymap", found_km)
            row.prop(found_kmi, "type", text="", full_event=True, emboss=True)
    
    leader_box.separator()

    col.separator()

    # Context sub-tabs
    row = col.row(align=True)
    row.prop_enum(prefs, "mapping_context_tab", "VIEW_3D", icon="OBJECT_DATAMODE")
    row.prop_enum(prefs, "mapping_context_tab", "VIEW_3D_EDIT", icon="EDITMODE_HLT")
    row.prop_enum(prefs, "mapping_context_tab", "GEOMETRY_NODE", icon="GEOMETRY_NODES")
    row.prop_enum(prefs, "mapping_context_tab", "SHADER_EDITOR", icon="NODE_MATERIAL")
    row.prop_enum(prefs, "mapping_context_tab", "IMAGE_EDITOR", icon="UV")
    col.separator()

    # Action bar
    row = col.row(align=True)
    row.scale_y = 1.5
    op = row.operator("chordsong.mapping_add", text="Add New Chord", icon="ADD")
    op.context = prefs.mapping_context_tab
    row.separator()
    op = row.operator("chordsong.check_conflicts", text="Check for Conflicts", icon='ERROR')
    row.separator()
    op = row.operator("chordsong.group_add", text="Add New Group", icon="ADD")
    op.name = "New Group"
    row.separator()
    row.operator("chordsong.group_cleanup", text="", icon="BRUSH_DATA")
    row.separator()
    row.operator("chordsong.group_fold_all", text="", icon="TRIA_UP_BAR")
    row.separator()
    row.operator("chordsong.group_unfold_all", text="", icon="TRIA_DOWN_BAR")

    col.separator()

    # Search box
    search_row = col.row(align=True)
    search_row.scale_y = 1.2
    search_row.operator("chordsong.mapping_fold_all", text="", icon="TRIA_UP_BAR", emboss=False)
    search_row.separator()
    search_row.operator("chordsong.mapping_unfold_all", text="", icon="TRIA_DOWN_BAR", emboss=False)
    search_row.separator()
    search_row.prop(prefs, "chord_search", text="", icon="VIEWZOOM", placeholder="Search chords, labels, operators, properties, toggles, scripts...")
    if prefs.chord_search:
        search_row.operator("chordsong.clear_search", text="", icon="X", emboss=False)

    col.separator()

    # Filter mappings by selected context tab and search query
    current_context = prefs.mapping_context_tab
    search_query = (prefs.chord_search or "").strip().lower()

    def _matches_search(m, query):
        """Check if a mapping matches the search query."""
        if not query:
            return True
        
        # Search in chord
        chord_str = get_str_attr(m, "chord") or ""
        if query in chord_str.lower():
            return True
        
        # Search in label
        label_str = get_str_attr(m, "label") or ""
        if query in label_str.lower():
            return True
        
        # Search based on mapping type
        mapping_type = getattr(m, "mapping_type", "OPERATOR")
        
        if mapping_type == "OPERATOR":
            # Search in operator ID
            operator_str = get_str_attr(m, "operator") or ""
            if query in operator_str.lower():
                return True
            # Search in sub-operators
            for sub_op in getattr(m, "sub_operators", []):
                sub_op_str = get_str_attr(sub_op, "operator") or ""
                if query in sub_op_str.lower():
                    return True
        
        elif mapping_type == "CONTEXT_PROPERTY":
            # Search in property path
            prop_path = get_str_attr(m, "context_path") or ""
            if query in prop_path.lower():
                return True
            # Search in property value
            prop_val = get_str_attr(m, "property_value") or ""
            if query in prop_val.lower():
                return True
            # Search in sub-items
            for sub_item in getattr(m, "sub_items", []):
                sub_path = get_str_attr(sub_item, "path") or ""
                sub_val = get_str_attr(sub_item, "value") or ""
                if query in sub_path.lower() or query in sub_val.lower():
                    return True
        
        elif mapping_type == "CONTEXT_TOGGLE":
            # Search in toggle path
            toggle_path = get_str_attr(m, "context_path") or ""
            if query in toggle_path.lower():
                return True
            # Search in sub-items
            for sub_item in getattr(m, "sub_items", []):
                sub_path = get_str_attr(sub_item, "path") or ""
                if query in sub_path.lower():
                    return True
        
        elif mapping_type == "PYTHON_FILE":
            # Search in script file path
            script_file = get_str_attr(m, "python_file") or ""
            if query in script_file.lower():
                return True
        
        return False

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        mapping_context = getattr(m, "context", "VIEW_3D")
        # Include mappings with matching context or "ALL" context
        if mapping_context != current_context and mapping_context != "ALL":
            continue
        
        # Apply search filter
        if not _matches_search(m, search_query):
            continue

        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    # Build group order from prefs.groups collection (user-defined order)
    # Groups in the collection come first (in order), then any remaining groups alphabetically
    group_order = []
    for grp in prefs.groups:
        if grp.name in groups:
            group_order.append(grp.name)
    # Add any groups not in the collection (e.g., "Ungrouped" or orphaned groups)
    remaining = [g for g in groups.keys() if g not in group_order]
    # Sort remaining: "Ungrouped" first, then alphabetically
    remaining.sort(key=lambda s: (s != "Ungrouped", s.lower()))
    group_order = remaining + group_order  # Ungrouped first, then user-ordered groups

    # Draw grouped UI boxes
    for group_name in group_order:
        items = groups[group_name]
        items.sort(
            key=lambda im: (
                get_str_attr(im[1], "chord").lower(),
                get_str_attr(im[1], "label").lower(),
            )
        )

        is_expanded, expand_data, expand_prop = _get_group_expansion_state(prefs, group_name)

        # Check if any mapping in this group has conflicts
        group_has_conflicts = any(
            _is_mapping_conflicted(m, prefs.mappings) for _, m in items
        )

        # Foldable header row
        header = col.row(align=True)

        # Split: Label (Left) | Buttons (Right)
        split = header.split(factor=0.6)

        # Left side: Expansion + Group Name
        row_left = split.row(align=True)
        if expand_data and expand_prop:
            row_left.prop(
                expand_data, expand_prop,
                icon="TRIA_DOWN" if is_expanded else "TRIA_RIGHT",
                text="",
                emboss=False,
            )

        # Show group icon if available
        group_icon = ""
        if group_name != "Ungrouped":
            for grp in prefs.groups:
                if grp.name == group_name:
                    group_icon = grp.icon
                    break
        
        # Show conflict indicator if group has conflicted chords
        if group_has_conflicts:
            row_left.alert = True
            if group_icon:
                row_left.label(text=f"{group_icon} {group_name}", icon="ERROR")
            else:
                row_left.label(text=f"{group_name}", icon="ERROR")
        else:
            if group_icon:
                row_left.label(text=f"{group_icon} {group_name}")
            else:
                row_left.label(text=f"{group_name}")

        # Right side: Buttons (compact and aligned right)
        row_right = split.row(align=True)
        row_right.alignment = 'RIGHT'

        # Add new chord button
        op = row_right.operator("chordsong.mapping_add", text="", icon="ADD", emboss=True)
        op.group = group_name
        op.context = prefs.mapping_context_tab
        row_right.separator()

        # Rename, Move, and Delete group buttons
        if group_name != "Ungrouped":
            group_idx = _get_group_index(prefs, group_name)
            if group_idx is not None:
                # Move up button
                op = row_right.operator("chordsong.group_move_up", text="", icon="TRIA_UP", emboss=False)
                op.index = group_idx
                # Move down button
                op = row_right.operator("chordsong.group_move_down", text="", icon="TRIA_DOWN", emboss=False)
                op.index = group_idx
                row_right.separator()
                # Edit group button (name and icon)
                op = row_right.operator("chordsong.group_edit", text="", icon="GREASEPENCIL", emboss=False)
                op.index = group_idx
                row_right.separator()
                # Delete group button
                op = row_right.operator("chordsong.group_remove", text="", icon="TRASH", emboss=False)
                op.index = group_idx

        if not is_expanded:
            continue

        col.separator()
        # Pass all mappings for conflict checking
        for idx, m in items:
            draw_mapping_item(prefs, m, idx, col, all_mappings=prefs.mappings)
            # Extra spacing between item boxes
            col.separator(factor=2.0)

    col.separator()

def _get_group_expansion_state(prefs, group_name):
    """Retrieve expansion state for a group."""
    if group_name == "Ungrouped":
        return prefs.ungrouped_expanded, prefs, "ungrouped_expanded"

    for grp in prefs.groups:
        if grp.name == group_name:
            return grp.expanded, grp, "expanded"

    return True, None, None

def _get_group_index(prefs, group_name):
    """Retrieve group index by name."""
    for idx, grp in enumerate(prefs.groups):
        if grp.name == group_name:
            return idx
    return None
