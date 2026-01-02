# Mappings

Configure chord mappings for operators, properties, scripts, and context toggles.

## Adding Mappings

There are several ways to create chord mappings:

1.  **Right-Click**: Right-click any button or property in Blender and select **Add Chord Mapping**.
2.  **Info Panel**: Extract actions from Blender's history ([Info Editor](../features/info.md)) to batch-create mappings.
3.  **Preferences**: Manually add and edit mappings in the Chord Song tab.
4.  **JSON File**: Manually edit the `mappings.json` file. You can open its location by **Alt+Clicking** the folder icon next to the path in preferences.

## Mapping Properties

Every mapping consists of the following properties:

- **Chord**: The key sequence (e.g., `g g`).
- **Label**: The name shown in the overlay.
- **Icon**: A font icon (Nerd Fonts) to display next to the label. Can be any ASCII symbol.
- **Group**: Optional category to organize your overlay into sections.
- **Context**: The Blender editor where the mapping is active (3D View, Shader Editor, etc.).

## Mapping Types

- [Operator Mapping](mappings/operator.md)
- [Property Mapping](mappings/property.md)
- [Toggle Mapping](mappings/toggle.md)
- [Script Mapping](mappings/script.md)
