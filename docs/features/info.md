# Adding Chords from Info Panel

Use Blender's Info panel to quickly create chord mappings from operator history.

## Overview

The Info panel displays Python code for every operator call and property assignment in Blender. Chord Song can extract this information to automatically create mappings, allowing you to batch-create multiple chord mappings at once.

## Accessing the Info Panel

1. Open Blender's **Info** editor (Window > Toggle System Console, or add an Info editor area).
2. The Info panel shows Python code for all operations you perform in Blender.

## Workflow

### Step 1: Perform Actions

Execute operators or change properties in Blender. Each action appears in the Info panel as Python code:

**Operators:**
```
bpy.ops.mesh.primitive_cube_add()
bpy.ops.object.shade_smooth()
bpy.ops.transform.translate(value=(1, 0, 0))
```

**Properties:**
```
bpy.context.scene.cycles.use_denoising = True
bpy.context.space_data.overlay.show_wireframes = False
```

### Step 2: Select Text in Info Panel

1. In the Info panel, select one or more lines containing operators or properties.
2. Right-click on the selected text.
3. Choose **"Add Chord Mapping"** from the context menu.

### Step 3: Configure the Mapping

The Chord Song dialog will appear with:
- **Operator/Property**: Automatically extracted from the selected text
- **Editor Context**: Auto-detected based on the current editor
- **Label**: Auto-generated from the operator/property name
- **Group**: Auto-suggested based on the mapping type

You can then:
- Enter your desired chord sequence
- Adjust the label and group
- Modify the editor context if needed
- Add operator arguments or property values

## Batch Creation

When you select multiple lines in the Info panel:

- **Multiple Operators**: All selected operators are extracted. The first becomes the primary mapping, and others are stored as sub-items that can be converted to separate mappings.
- **Multiple Properties**: All selected properties are extracted. The first becomes the primary mapping, and others are stored as sub-items.

## Supported Formats

### Operators

Chord Song recognizes these operator formats:
- `bpy.ops.module.operator_name()`
- `module.operator_name()`
- `module.operator_name(arg="value")`

### Properties

Chord Song recognizes these property formats:
- `bpy.context.path.to.property = value`
- `bpy.data.path.to.property = value`
- `path.to.property = value`

## Tips

- **Select Multiple Lines**: Hold Shift and drag to select multiple operations for batch creation
- **Copy to Clipboard**: You can also copy text to the clipboard and use the context menu - Chord Song will read from the clipboard
- **Mixed Types**: If you select both operators and properties, Chord Song will process them separately based on the first item's type
- **Auto-Detection**: The system automatically detects whether a property is a boolean (toggle) or other value type

## Example Workflow

1. Perform several operations: Add a cube, shade smooth, enable wireframes
2. Open Info panel and see:
   ```
   bpy.ops.mesh.primitive_cube_add()
   bpy.ops.object.shade_smooth()
   bpy.context.space_data.overlay.show_wireframes = True
   ```
3. Select all three lines, right-click, choose "Add Chord Mapping"
4. For each item, enter a chord (e.g., `c`, `s`, `w`) and configure as needed
5. All mappings are created automatically with proper context detection
