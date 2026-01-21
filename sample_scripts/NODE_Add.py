# pylint: disable=undefined-variable
# ruff: noqa: F821

import bpy

def main():
    # Logging to help us confirm things are working
    print("\n" + "="*40)
    print("CHORD SONG: Executing Generic Node Adder")
    print(f"Combined Params: {args}")

    # 1. Get the Node ID and options
    node_id = args.get("id", "NodeReroute")
    use_transform = args.get("use_transform", False)
    
    space = context.space_data
    if not space or space.type != 'NODE_EDITOR':
        print("Error: Not in a Node Editor")
        return

    tree = space.edit_tree
    if not tree:
        print("Error: No active node tree")
        return

    # 2. Add the node
    node = None
    try:
        if use_transform:
            # Use operator to allow interactive placement (stick-to-mouse)
            bpy.ops.node.add_node('INVOKE_DEFAULT', use_transform=True, type=node_id)
            node = tree.nodes.active
            print(f"Invoked add_node: {node_id}")
        else:
            # Standard creation at cursor
            node = tree.nodes.new(type=node_id)
            node.location = space.cursor_location if hasattr(space, 'cursor_location') else (0, 0)
            print(f"Created: {node_id}")
    except Exception as e:
        print(f"Error: Failed to create node '{node_id}': {e}")
        return

    if not node:
        return

    # 3. Apply properties
    # We set these first as they change what other properties are available (e.g. data_type)
    priority_keys = ["data_type", "blend_type", "operation"]
    
    # Track keys that we have already applied
    applied = {"id", "use_transform"}

    # Pass 1: Set priority keys
    for key in priority_keys:
        if key in args:
            val = args[key]
            if hasattr(node, key):
                try:
                    setattr(node, key, val)
                    print(f"Set priority property: {key} = {val}")
                except Exception as e:
                    print(f"Error setting priority {key}: {e}")
            applied.add(key)

    # Pass 2: Set all other properties from args
    for key, value in args.items():
        if key not in applied:
            if hasattr(node, key):
                try:
                    setattr(node, key, value)
                    print(f"Set property: {key} = {value}")
                except Exception as e:
                    print(f"Error setting {key}: {e}")
            else:
                print(f"Warning: Property '{key}' not found on {node_id}")
    
    # Finalize selection
    for n in tree.nodes:
        n.select = False
    node.select = True
    tree.nodes.active = node

    print(f"Successfully configured: {node_id}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
