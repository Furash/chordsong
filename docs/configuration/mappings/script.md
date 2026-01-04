# Script Mappings

Map chords to Python scripts.

## Overview

Script mappings execute external or internal Python scripts, enabling custom workflows and macros.

### Creating Script Mappings

See [Adding Mappings](../mappings.md#adding-mappings) for general methods. Script mappings are typically created manually in Preferences.

### Scripts Folder

To streamline your workflow, you can define a **Scripts Folder** in the [Customization](../../customization.md#preferences) section.

When configuring a Script Mapping:

1. Click the **folder icon** next to the Python File path.
2. A searchable popup will appear listing all `.py` files in your configured scripts folder.
3. Selecting a file will automatically update the mapping's path and label.

### Script Arguments & Parameters

Chord Song allows you to pass custom data to your scripts using a dictionary named `args`. This is extremely powerful for creating versatile scripts that behave differently depending on the chord used.

#### Accessing `args` in Python

Inside your script, access the passed values using the global `args` dictionary:

```python
import bpy

# Access parameters passed from Chord Song
node_id = args.get("id", "NodeReroute")
use_transform = args.get("use_transform", False)

print(f"Adding node: {node_id}")
```

### Advanced Workflow

The included `sample_scripts/NODE_Add.py` demonstrates how to pass arguments to a script. It uses `args` to do so. So you can use it as a template for your own scripts with custom parameters.

You can use the mapping UI to add parameters to your script.
They can be comma separated or added as individual rows using `+` button.

<!-- markdownlint-disable MD033 -->
<img src="/chordsong/scr/scripts.png" alt="Script Params">
<!-- markdownlint-enable MD033 -->







