"""Nerd Font icons collection for Blender/3D operations."""

# Collection of (name, icon_character) tuples
NERD_ICONS = [
    # 3D Objects & Primitives
    ("Cube", "󰆧"),
    ("Sphere", ""),
    ("Circle", ""),
    ("Polygon", "󰙞"),
    ("Hexagon", "󰋙"),
    ("Triangle", "󰔶"),
    ("Square", "󰝤"),
    ("Diamond", "󰇈"),
    ("Cylinder", "󱥎"),
    ("Torus", ""),
    ("Cone", "󱥌"),
    ("Pyramid", "󱥒"),
    
    # Mesh & Geometry
    ("Mesh", "󰕠"),
    ("Vertices", "󰕡"),
    ("Edges", "󰐡"),
    ("Grid", "󰝘"),
    ("Wireframe", ""),
    ("Shape", "󰠱"),
    ("Path", "󰴠"),
    ("Curve", "󰫨"),
    
    # File & Folder Operations
    ("File", "󰈔"),
    ("File Open", "󰷏"),
    ("File New", ""),
    ("File Save", "󰆓"),
    ("Folder", "󰉋"),
    ("Folder Open", "󰝰"),
    ("Folders", "󰉓"),
    ("Import", ""),
    ("Export", ""),
    ("Download", "󰇚"),
    ("Upload", "󰕒"),
    ("Archive", "󰀼"),
    ("Package", "󰏗"),
    
    # Git & Version Control
    ("Git", "󰊢"),
    ("GitHub", ""),
    ("Branch", "󰘬"),
    ("Merge", ""),
    ("Commit", "󰜘"),
    ("Pull", "󰶡"),
    ("Push", "󰶣"),
    ("Diff", ""),
    ("History", "󰋚"),
    
    # Camera & View
    ("Camera", "󰄀"),
    ("Camera Alt", ""),
    ("Eye", "󰈈"),
    ("Eye Off", "󰈉"),
    ("View", "󰄄"),
    ("Fullscreen", "󰊓"),
    ("Zoom In", ""),
    ("Zoom Out", ""),
    ("Crosshair", ""),
    
    # Transform & Edit
    ("Move", "󰜷"),
    ("Arrows", "󰘁"),
    ("Rotate", "󰑓"),
    ("Scale", "󰩨"),
    ("Resize", "󰙖"),
    ("Transform", "󰩨"),
    ("Cursor", "󰇀"),
    ("Select", "󰒅"),
    ("Deselect", "󱟁"),
    
    # Edit Tools
    ("Edit", "󰤌"),
    ("Pencil", "󰏫"),
    ("Pen", ""),
    ("Brush", "󰌑"),
    ("Eraser", ""),
    ("Scissors", "󰩫"),
    ("Knife", "󰧻"),
    ("Crop", "󰩬"),
    ("Duplicate", ""),
    ("Copy", "󰆏"),
    ("Paste", "󰆒"),
    ("Puzzle", "󰐱"),
    
    # Materials & Shading
    ("Material", ""),
    ("Shader", "󰌁"),
    ("Palette", "󰏘"),
    ("Color", "󰏘"),
    ("Gradient", "󱝊"),
    ("Texture", "󰿦"),
    ("Image", "󰥶"),
    ("Layers", ""),
    ("Eyedropper", ""),
    
    # Lighting
    ("Light", "󰛨"),
    ("Sun", "󰖙"),
    ("Spotlight", "󰓉"),
    ("Flash", "󱐋"),
    ("Brightness", "󰃟"),
    
    # Animation & Timeline
    ("Animation", "󰐎"),
    ("Keyframe", "󰐕"),
    ("Clock", "󰥔"),
    ("Play", "󰐊"),
    ("Pause", "󰏤"),
    ("Stop", "󰓛"),
    ("Record", "󰑊"),
    ("Skip Forward", "󰒭"),
    ("Skip Back", "󰒮"),
    ("Fast Forward", "󰒫"),
    ("Rewind", "󰑟"),
    
    # Rendering
    ("Render", "󰹑"),
    ("Film", "󰕧"),
    
    # Modifiers & Effects
    ("Modifier", ""),
    ("Array", "󱗼"),
    ("Mirror", ""),
    ("Boolean", ""),
    ("Subdivision", "󰕰"),
    ("Bevel", "󰘇"),
    ("Wave", "󰥛"),
    ("Sparkle", ""),
    
    # Physics & Simulation
    ("Physics", ""),
    ("Particle", "󰙥"),
    ("Fire", "󰈸"),
    ("Water", "󰖌"),
    ("Fluid", ""),
    ("Smoke", ""),
    ("Cloud", ""),
    ("Wind", "󰖝"),
    
    # Constraints & Rigging
    ("Link", "󰌷"),
    ("Chain", ""),
    ("Bone", ""),
    ("Joint", "󰴼"),
    ("Anchor", ""),
    ("Lock", "󰌾"),
    ("Unlock", ""),
    
    # UI & Navigation
    ("Menu", "󰮫"),
    ("Hamburger", "󰚅"),
    ("Dots Vertical", "󰇙"),
    ("Dots Horizontal", "󰇘"),
    ("Search", "󰍉"),
    ("Filter", "󰈲"),
    ("Settings", "󰒓"),
    ("Gear", ""),
    ("Sliders", ""),
    ("Wrench", ""),
    ("Tool", "󱌣"),
    
    # Actions
    ("Add", ""),
    ("Plus", "󰐕"),
    ("Remove", "󱝧"),
    ("Minus", "󰍴"),
    ("Delete", ""),
    ("Trash", "󰆴"),
    ("Close", "󰅖"),
    ("X", "󰅖"),
    ("Check", ""),
    ("Checkmark", "󰄬"),
    
    # Arrows & Navigation
    ("Arrow Up", "󰁝"),
    ("Arrow Down", "󰁅"),
    ("Arrow Left", "󰁍"),
    ("Arrow Right", "󰁔"),
    ("Undo", "󰕌"),
    ("Redo", "󰑎"),
    ("Refresh", "󰑓"),
    ("Sync", "󰓦"),
    
    # Information & Status
    ("Info", "󰋽"),
    ("Help", "󰋖"),
    ("Question", "󰘥"),
    ("Warning", ""),
    ("Alert", "󰀪"),
    ("Error", "󰅖"),
    ("Success", "󰄬"),
    ("Star", "󰓎"),
    ("Bookmark", "󰃀"),
    ("Tag", "󰓹"),
    
    # Development
    ("Code", ""),
    ("Terminal", ""),
    ("Console", "󰆍"),
    ("Python", "󰌠"),
    ("Script", "󰯂"),
    ("Bug", "󰃤"),
    ("Debug", "󰃤"),
    
    # Miscellaneous
    ("Pin", "󰐃"),
    ("Magnet", ""),
    ("Target", ""),
    ("Crosshairs", "󰓾"),
    ("Dashboard", "󰕮"),
    ("Chart", "󰄪"),
    ("Graph", "󱁉"),
    ("Database", "󰆼"),
    ("Server", "󰒋"),
    ("Box", "󰆧"),
    ("Package Box", "󰏗"),
]
