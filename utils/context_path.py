"""Path normalization utilities for property and context paths."""
import re

def normalize_bpy_data_path(path):
    """Normalize bpy.data paths to context-relative paths.
    
    Converts patterns like scenes["Scene"] -> scene, worlds["World"] -> world, etc.
    Removes bpy.data. prefix and indexed collection access, converting plural to singular.
    
    Args:
        path: Property path string (may include bpy.data. prefix)
    
    Returns:
        Normalized path string
    
    Examples:
        >>> normalize_bpy_data_path('bpy.data.scenes["Scene"].ADDON.toggleSomething')
        'scene.ADDON.toggleSomething'
        >>> normalize_bpy_data_path('scenes["Scene"].ADDON.something')
        'scene.ADDON.something'
        >>> normalize_bpy_data_path('bpy.data.worlds["World"].use_nodes')
        'world.use_nodes'
    """
    cleaned_path = path
    
    # Remove bpy.data. prefix if present
    if cleaned_path.startswith("bpy.data."):
        cleaned_path = cleaned_path[len("bpy.data."):]
    
    # Remove indexed collection access and convert to singular
    # Pattern: collection_name["index"].rest_of_path -> singular.rest_of_path
    # This works whether or not the path had bpy.data. prefix
    match = re.match(r'^(\w+)\[[^\]]+\]\.(.+)$', cleaned_path)
    if match:
        collection_name = match.group(1)
        rest_of_path = match.group(2)
        # Convert plural to singular: remove trailing 's'
        singular = collection_name[:-1] if collection_name.endswith('s') else collection_name
        cleaned_path = f'{singular}.{rest_of_path}'
    
    return cleaned_path
