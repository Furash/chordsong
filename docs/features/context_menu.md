# Context Menu Integration

Create mappings from Blender's context menu.

## Accessing the Context Menu

Right-click any UI element to create a mapping.

<!-- markdownlint-disable MD033 -->
<img src="../../scr/add_chord_rmb.png" alt="Context Menu" width="200">
<!-- markdownlint-enable MD033 -->

The pop up will appear with the following fields

<!-- markdownlint-disable MD033 -->
<img src="../../scr/add_chord_rmb_menu.png" alt="Add Chord Popup">
<!-- markdownlint-enable MD033 -->

- **Enter Chord**: The sequence of keys that will trigger the mapping.
- **Editor Context**: Context in which the mapping will be active.
- **Label**: Chord name.
- **Group**: Chord group.
- **Parameters**: Operator parameters.

!!! note "Parameters Automatic Detection"
    If the operator is detected successfully, the parameters will be filled automatically. The non-conflicting chord will be also suggested based on the operator name.
