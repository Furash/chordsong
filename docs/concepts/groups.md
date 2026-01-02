# Groups

Groups organize chord mappings into logical categories for easier management.

## Visual Organization

- **Preferences UI**: Collapsible sections let you fold/unfold groups to focus on specific categories.

<!-- markdownlint-disable MD033 -->
<img src="../scr/groups_prefs_ui.gif" alt="Groups in Preferences">
<!-- markdownlint-enable MD033 -->

- **Overlay Display**: When multiple mappings share a token prefix, the overlay shows which groups contain them.

<!-- markdownlint-disable MD033 -->
<img src="../scr/groups_overlay.png" alt="Groups in Overlay" width="300">
<!-- markdownlint-enable MD033 -->

## Group Management

### Adding Groups

Groups can be created:

1. **Manually**: Click **Add New Group** in the Mappings tab.
    - Go to **Edit > Preferences > Addons > Chord Song > Mappings**. `<Leader> k c` by default.
    - Click **Add New Group**.
    - Enter a group name.
2. **Automatically**: Assigning a group name to a mapping creates the group if it doesn't exist. Unreal Engine style.
3. **From JSON**: Groups are created when loading mappings from a JSON file.

### Removing Groups

1. Click the trash icon next to a group name.
2. If the group contains mappings, choose:
   - **Reassign**: Move mappings to another group.
   - **Clear**: Remove group assignment (mappings become "Ungrouped").
   - **Delete**: Permanently remove the group and all its mappings.

!!! warning "Deletion is Permanent"
    Cannot be undone. Consider reassigning mappings instead.

### Renaming Groups

1. Click the rename button (A icon) next to a group name.
2. Enter the new name in the dialog.
3. Click **OK** to confirm.

!!! tip "Naming Convention"
    Use descriptive names like "Editing" or "Navigation". Group names are case-sensitive.

All mappings using the old group name are automatically updated to use the new name.

### Cleaning Up Groups

The **Clean Up Groups** button (brush icon) automatically:

- Removes duplicate groups.
- Removes empty groups.

Use periodically to keep groups tidy, especially after importing configurations.

### Folding and Unfolding

- **Fold All**: Collapse all groups to show headers only.
- **Unfold All**: Expand all groups to show all mappings.

### Ungrouped Mappings

Mappings without a group assignment are placed in **"Ungrouped"**:

- Appears at the top of the list.
- Can be folded/unfolded like other groups.
