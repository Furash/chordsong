import bpy

class NODE_OT_Add_VectorMath(bpy.types.Operator):
    """Add a Vector Math node with a specific operation"""
    bl_idname = "node.add_vector_math"
    bl_label = "Add Vector Math Node"
    bl_options = {'REGISTER', 'UNDO'}

    operation: bpy.props.EnumProperty(
        name="Operation",
        items=[
            # Standard
            ('ADD', "Add", "Add two vectors"),
            ('SUBTRACT', "Subtract", "Subtract two vectors"),
            ('MULTIPLY', "Multiply", "Multiply two vectors"),
            ('DIVIDE', "Divide", "Divide two vectors"),
            ('MULTIPLY_ADD', "Multiply Add", "Multiply two vectors and add a third"),
            
            # Vector Ops
            ('CROSS_PRODUCT', "Cross Product", "Calculate the cross product of two vectors"),
            ('PROJECT', "Project", "Project one vector onto another"),
            ('REFLECT', "Reflect", "Reflect a vector off a surface normal"),
            ('REFRACT', "Refract", "Refract a vector through a surface normal"),
            ('FACEFORWARD', "Faceforward", "Orient a vector to face forward"),
            ('DOT_PRODUCT', "Dot Product", "Calculate the dot product of two vectors"),
            
            # Distance/Length
            ('DISTANCE', "Distance", "Calculate the distance between two vectors"),
            ('LENGTH', "Length", "Calculate the length of a vector"),
            ('SCALE', "Scale", "Scale a vector by a factor"),
            ('NORMALIZE', "Normalize", "Normalize a vector (length = 1)"),
            
            # Comparison/Truncation
            ('ABSOLUTE', "Absolute", "Absolute value of each component"),
            ('POWER', "Power", "Power of each component"),
            ('SIGN', "Sign", "Sign of each component"),
            ('MINIMUM', "Minimum", "Minimum of two vectors"),
            ('MAXIMUM', "Maximum", "Maximum of two vectors"),
            ('FLOOR', "Floor", "Floor of each component"),
            ('CEIL', "Ceil", "Ceil of each component"),
            ('FRACTION', "Fraction", "Fractional part of each component"),
            ('MODULO', "Modulo", "Modulo of each component"),
            ('WRAP', "Wrap", "Wrap each component"),
            ('SNAP', "Snap", "Snap each component to a multiple"),
            
            # Trigonometry
            ('SINE', "Sine", "Sine of each component"),
            ('COSINE', "Cosine", "Cosine of each component"),
            ('TANGENT', "Tangent", "Tangent of each component"),
        ],
        default='ADD'
    )

    def execute(self, context):
        # Determine the node type based on the active node tree
        space = context.space_data
        if not space or space.type != 'NODE_EDITOR':
            self.report({'ERROR'}, "Must be in a Node Editor")
            return {'CANCELLED'}
        
        tree = space.edit_tree
        if not tree:
            self.report({'ERROR'}, "No active node tree")
            return {'CANCELLED'}

        # Map tree types to their corresponding Vector Math node identifiers
        node_map = {
            'ShaderNodeTree': 'ShaderNodeVectorMath',
            'GeometryNodeTree': 'GeometryNodeVectorMath',
            'CompositorNodeTree': 'CompositorNodeVectorMath',
            'TextureNodeTree': 'TextureNodeVectorMath',
        }
        
        node_type = node_map.get(tree.bl_rna.name, 'ShaderNodeVectorMath')
        
        # Add the node
        bpy.ops.node.add_node(type=node_type, use_transform=True)
        
        # The add_node operator makes the new node active
        node = tree.nodes.active
        if node and hasattr(node, "operation"):
            node.operation = self.operation
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(NODE_OT_Add_VectorMath)

def unregister():
    bpy.utils.unregister_class(NODE_OT_Add_VectorMath)

if __name__ == "__main__":
    register()
