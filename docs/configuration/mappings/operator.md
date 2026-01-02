# Operator Mappings

The **Operator Mappings** allow you to bind standard Blender commands to chord sequences.

## Adding Operators

There are three primary ways to capture operators:

1. **Context Menu (RMB)**: Right-click any button or menu item in Blender and select **Add Chord Mapping**.
2. **Preferences Panel**: Use the **Add Mapping** button in the Chord Song preferences to manually define an operator ID.
3. **Info Panel**: Select one or more rows of operator history in Blender's Info Editor, right-click, and select **Extract to Chord Mapping**.

## Chaining Multiple Operators

Chord Song allows you to execute a sequence of operators with a single chord. This is ideal for complex macros (e.g., "Duplicate > Move > Rename").

### Setting up a Chain:
1. Set the **Mapping Type** to **Operator**.
2. Use the **+** (Add) button next to the operator field to add **Sub-Operators**.
3. Operators are executed in descending order.

```python
# Example of a chained execution flow:
# 1. Duplicate the object
# 2. Shade it smooth
# 3. Enter Edit mode
bpy.ops.object.duplicate()
bpy.ops.object.shade_smooth()
bpy.ops.object.editmode_toggle()
```

## Configuration Properties

| Property | Description |
| :--- | :--- |
| **Operator ID** | The path starting with `bpy.ops` (e.g., `mesh.subdivide`). |
| **Parameters** | A Python-style dictionary for arguments (e.g., `number_cuts=2`). |
| **Call Context** | `Exec` runs the command immediately; `Invoke` may open a secondary UI or tool-setting popup. |
