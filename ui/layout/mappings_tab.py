"""
Mappings tab for addon preferences.
"""

from ...core.engine import get_str_attr
from .mapping_item import draw_mapping_item

def draw_mappings_tab(prefs, context, layout):
    """Draw the Mappings tab content."""
    col = layout.column()
    
    # Leader Key section
    kc = context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.get("3D View")
        if km:
            kmi = None
            for item in km.keymap_items:
                if item.idname == "chordsong.leader":
                    kmi = item
                    break

            if kmi:
                leader_box = col.box()
                split = leader_box.split(factor=0.5)

                # Leader Key section
                leader_col = split.column()
                leader_row = leader_col.row(align=True)
                leader_row.scale_y = 1.2
                leader_row.label(text="Leader Key:")
                leader_row.scale_y = 1.5
                leader_row.scale_x = 1.5
                leader_row.context_pointer_set("keymap", km)
                leader_row.prop(kmi, "type", text="", full_event=True, emboss=True)
                leader_row.separator()

                # Conflict checker section
                conflict_col = split.column()
                conflict_row = conflict_col.row(align=True)
                conflict_row.scale_y = 1.2
                conflict_row.label(text="Conflict Checker:")
                conflict_row.scale_y = 1.5
                conflict_row.operator("chordsong.check_conflicts", text="Check for Conflicts", icon="ERROR")
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
    op = row.operator("chordsong.group_add", text="Add New Group", icon="ADD")
    op.name = "New Group"
    row.separator()
    row.operator("chordsong.group_cleanup", text="", icon="BRUSH_DATA")
    row.separator()
    row.operator("chordsong.group_fold_all", text="", icon="TRIA_UP")
    row.operator("chordsong.group_unfold_all", text="", icon="TRIA_DOWN")
    
    col.separator()


    # Filter mappings by selected context tab
    current_context = prefs.mapping_context_tab

    groups = {}
    for idx, m in enumerate(prefs.mappings):
        mapping_context = getattr(m, "context", "VIEW_3D")
        if mapping_context != current_context:
            continue

        group = get_str_attr(m, "group") or "Ungrouped"
        groups.setdefault(group, []).append((idx, m))

    # Draw grouped UI boxes
    for group_name in sorted(groups.keys(), key=lambda s: (s != "Ungrouped", s.lower())):
        items = groups[group_name]
        items.sort(
            key=lambda im: (
                get_str_attr(im[1], "chord").lower(),
                get_str_attr(im[1], "label").lower(),
            )
        )

        is_expanded, expand_data, expand_prop = _get_group_expansion_state(prefs, group_name)

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
        row_left.label(text=f"{group_name}")

        # Right side: Buttons (compact and aligned right)
        row_right = split.row(align=True)
        row_right.alignment = 'RIGHT'
        
        # Add new chord button
        op = row_right.operator("chordsong.mapping_add", text="", icon="ADD", emboss=True)
        op.group = group_name
        op.context = prefs.mapping_context_tab
        row_right.separator()
        
        # Rename and Delete group buttons
        if group_name != "Ungrouped":
            group_idx = _get_group_index(prefs, group_name)
            if group_idx is not None:
                # Rename group button
                op = row_right.operator("chordsong.group_rename", text="", icon="EVENT_A", emboss=False)
                op.index = group_idx
                row_right.separator()
                # Delete group button
                op = row_right.operator("chordsong.group_remove", text="", icon="TRASH", emboss=False)
                op.index = group_idx

        if not is_expanded:
            continue

        col.separator()
        for idx, m in items:
            draw_mapping_item(prefs, m, idx, col)
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
