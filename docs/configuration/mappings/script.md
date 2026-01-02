## Script Mappings

Map chords to Python scripts.

### Overview

Script mappings execute external or internal Python scripts, enabling custom workflows and macros.

### Creating Script Mappings

### Scripts Folder

To streamline your workflow, you can define a **Scripts Folder** in the [Customization](../customization.md#preferences) section. 

When configuring a Script Mapping:
1.  Click the **folder icon** next to the Python File path.
2.  A searchable popup will appear listing all `.py` files in your configured scripts folder.
3.  Selecting a file will automatically update the mapping's path and label.

### Script Arguments & Parameters

Chord Song allows you to pass custom data to your scripts using a dictionary named `args`. This is extremely powerful for creating versatile scripts that behave differently depending on the chord used.

#### Defining Parameters
You can define parameters in two ways:
1.  **Parameters Field**: A comma-separated string like `id='NodeReroute', use_transform=True`.
2.  **Script Params List**: Add individual rows for more complex configurations (e.g., setting multiple properties).

#### Accessing `args` in Python
Inside your script, access the passed values using the global `args` dictionary:

```python
import bpy

# Access parameters passed from Chord Song
node_id = args.get("id", "NodeReroute")
use_transform = args.get("use_transform", False)

print(f"Adding node: {node_id}")
```

### Advanced Workflow: NODE_Add.py

The included `sample_scripts/NODE_Add.py` demonstrates a professional-grade node adder. It uses `args` to:
1.  Identify which node type to create.
2.  Decide whether to use the transform (interactive placement) operator.
3.  Bulk-apply priority settings like `blend_type` or `operation`.
4.  Dynamically map any additional keys in `args` directly to the node's properties.

### Execution Environment

When Chord Song executes your script, it provides the following globals:

- `bpy`: The Blender Python API.
- `context`: The current Blender context.
- `args`: A dictionary containing your defined parameters.
- `__file__`: The path to your script.
- `__name__`: Set to `"__main__"`.

!!! tip "Viewport Context"
    Chord Song automatically captures and restores the viewport context (view matrix, region, area) before running your script. This ensuring that `bpy.ops` commands within your script target the correct editor even if the user moved the mouse since triggering the chord.
