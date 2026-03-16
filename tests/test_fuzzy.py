"""Tests for fuzzy matching used by scripts overlay.

Uses the real script list from b:/scripts/iops_exec to verify
fuzzy_match returns expected results for various user inputs.
"""

import sys
import os

# Add parent dir so we can import utils.fuzzy without Blender
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.fuzzy import fuzzy_match

# ---------------------------------------------------------------------------
# Real script names from b:\scripts\iops_exec (without .py)
# ---------------------------------------------------------------------------
ALL_SCRIPTS = [
    "1_What",
    "2_Open_Current_Folder",
    "3D_Cursor_Reset",
    "3D_Cursor_To_Custom",
    "ANIMATION_Rename_Actions",
    "ANIM_Clear_ApplyT_Reparent",
    "ANIM_Delete_Scale_Keyframes",
    "ASSET_Export_Selected_FBX",
    "ASSET_Import_Selected",
    "ASSET_Update_Thumbs_by_Name",
    "Add_Vertex_Color_Selected",
    "Apply_Mod_Subd",
    "Assign_Random_Hardops_Material_Selected",
    "BOOLEAN_Apply_Booleans",
    "BOOLEAN_Hide_Cutters",
    "BTB_Fill_High_With_Mockups",
    "CCP_Anim_Export_Permutations",
    "CCP_Asset_Move",
    "CCP_Clean_Old_Props",
    "CCP_Clips",
    "CCP_Create_Light_By_Faces",
    "CCP_Ellipsoid_to_txt",
    "CCP_Prepare_SOF_Asteroid_Small",
    "CCP_Prepare_SOF_Structure_Gen_BIG",
    "CCP_Prepare_SOF_Structure_Gen_MID",
    "CCP_Q_D_Remap",
    "CCP_Replace_Selected_With_Active",
    "CCP_Replace_With_Library_Materials",
    "CCP_Set_DB_STAGING",
    "CCP_Source_Path_From_TXT",
    "CCP_Sprite_Phase_Offset_Cursor",
    "CCP_Sprite_Phase_Offset_Noise",
    "CCP_Sprite_Phase_Offset_X",
    "CCP_Sprite_Phase_Offset_Y",
    "CCP_Sprite_Phase_Offset_Z",
    "CCP_UV3_Checker_Toggle",
    "CCP_blinkPhase_random",
    "CHECK_Empties_Not_Touching_Geometry",
    "CLEAN_Auto_Smooth_Socket",
    "CLEAN_CH2_to_Lightmap",
    "CLEAN_Clear_Custom_Normals_Selected",
    "CLEAN_Console",
    "CLEAN_DataBlock",
    "CLEAN_Dead_Booleans_Cleaner",
    "CLEAN_Delete_Duplicate_Workspace",
    "CLEAN_Delete_Empty_Materials",
    "CLEAN_Delete_Mirror_Selected",
    "CLEAN_Deltas_Cleaner",
    "CLEAN_Drivers_Remove",
    "CLEAN_Edge_Data_Clear",
    "CLEAN_Materials_Backface_On",
    "CLEAN_Nuke_Stashes_Selected",
    "CLEAN_Object_Color",
    "CLEAN_Object_Color_All",
    "CLEAN_Remap_Duplicate_Textures_Materials",
    "CLEAN_Remap_Users_Selected",
    "CLEAN_Remap_Users_Selected_old",
    "CLEAN_Remove_Unused_Materials",
    "CLEAN_Select_Empty_Materials",
    "CLEAN_Select_NONE_TYPE",
    "CLEAN_Select_Sharp_Faces",
    "CLEAN_Select_ZERO_Armature",
    "CLEAN_Vertex_Color_Channel_Rename",
    "CLEAN_Vertex_Color_Remove",
    "CLEAN_Zero_Division_Drivers",
    "CLEAN_Zero_Tris_Objects",
    "COLLECTION_Export_Selected_Blend",
    "COLLECTION_From_Material_Names",
    "COLLECTION_Object_Color_From_Collection",
    "COLLECTION_Rename_From_Empty",
    "COLOR_Add",
    "COL_Rename_Selected",
    "DEBUG_Collections_By_Polycount",
    "DEBUG_Find_Users",
    "DEBUG_Show_Handlers",
    "DISPLAY_Toggle_Type",
    "EMPTY_Move_To_Bottom",
    "EXPORT_GR2",
    "FIX_Texture_Paths",
    "GEONODES_VertexColor_Blur",
    "IMAGE_Rename",
    "IMPORT_VDBs",
    "ImageAlphaNone",
    "Image_Save",
    "Instances_RED",
    "Isolate_Hide_Unhide",
    "JSON_Dump_Info_Selected",
    "LIGHT_Copy_Color_Active",
    "ListImageTextureNodes_2022",
    "MATERIALS_Default_Color",
    "MATERIALS_ID_Name_To_Color",
    "MATERIAL_Node_Parameters_Update",
    "MATERIAL_Remap_Local",
    "MATERIAL_Remove_All",
    "MATERIAL_Set_Emissive_White",
    "MATERIAL_Sort_ABC_Remap",
    "MATERIAL_Swap_to_GPU",
    "MATERIAL_Swap_to_OSL",
    "MATERIAL_shader_nodes_update",
    "MESH_Edge_Sharp_Toggle",
    "MESH_Korean_Corner_Convert",
    "MESH_Separate_By_Selected_Faces_Oriented",
    "MESH_m3_Cleanup_Selected",
    "MIPMAP_Closest",
    "MOD_Boolean_Apply_Active",
    "MOD_Boolean_Hide_Cutters",
    "MOD_Dead_Displace_Cleaner",
    "MOD_Del_Tri_Apply_All",
    "MOD_Enable_All",
    "MOD_Enable_Mirrors",
    "MOD_Korean_Bevel_Apply",
    "MOD_Korean_Bevel_Arc",
    "MOD_Mirror_Apply",
    "MOD_Mirror_Fix_Negative_Scale",
    "MOD_Mirror_Merge",
    "MOD_Remove_UV_Offset",
    "MOD_Smart_Apply",
    "MOD_Sort_Tri_Weight",
    "MOD_UV_Offset_Mirror",
    "MOD_Vertex_Group_Clean",
    "MOD_Vertex_Group_Rename",
    "Materials_From_Textures",
    "Multi_Link",
    "NAME_Objects_from_Collections",
    "NAME_Swap",
    "NF_Copy_Attr_Mod",
    "NF_Geodecal_Rename",
    "NF_Offset_Root_Collections_X",
    "NF_Offset_Root_Zero",
    "NF_Select_Root_Objects",
    "NODE_Add",
    "NODE_Add_Math",
    "NODE_Add_Percentage_Input",
    "NODE_Add_Vector_Math",
    "NODE_Break_Group_Input",
    "NODE_Copy_Color",
    "NODE_Match_Width_X",
    "NODE_Match_Width_XY",
    "NODE_Parallax_Amount",
    "NODE_Rename_Inputs_Panels",
    "NODE_Report_Non_Percentage_Floats",
    "NODE_Set_Label_Size",
    "Name_Selected_From_Active",
    "OBJECT_Pack_Spheres",
    "OBJECT_Random_Rot_Z",
    "OBJECT_Replace_With_Sphere",
    "OBJECT_Select_Grouped_Similar_Name",
    "OBJECT_Select_Similar_Name",
    "OPEN_Next_Blend_File",
    "OPEN_Previous_Blend_File",
    "OP_Repeat_On_Selected",
    "ORGANIZE_BTB_Children_To_Group",
    "OUTLINER_Create_Root_For_Selected",
    "ObjectData_Linker",
    "Objects_In_Grid",
    "PF_Bolts_Merge",
    "PF_Merge_Rename_Bolts",
    "PF_Outliner_Parent_Empty",
    "PF_Parent_to_Empty",
    "PIVOT_Center_Floor",
    "RENDER_Add_Stereo_Views",
    "RENDER_ByCamera",
    "RENDER_Hide_Viewport",
    "RENDER_Per_Material",
    "RENDER_Refresh_Thumbnail_XY",
    "RENDER_Save_IMG_Active_Collection_X",
    "RENDER_Save_IMG_Active_Collection_XY",
    "RENDER_Save_IMG_Active_Collection_Y",
    "RENDER_Save_IMG_Current_Camera",
    "RENDER_Unhide_Viewport",
    "Replace_With_Random",
    "SELECT_Linked_Data_Users",
    "SELECT_Mirror_Mod",
    "SELECT_Polycount",
    "SELECT_Reset_Filters",
    "SELECT_Shared_Data",
    "SELECT_Single_Data_User",
    "SELECT_Toggle_Empty",
    "SELECT_Toggle_Lights",
    "SELECT_Toggle_Mesh",
    "SELECT_Useless_Empties",
    "SELECT_Vertex_Color",
    "SELECT_Zero_Faces_Evaluated",
    "SORT_Collections_123",
    "SORT_Collections_ABC",
    "Scale_Median_Selected",
    "Select_Boolean_Target",
    "Select_High",
    "Select_Negative_Scale",
    "Select_Scaled_or_Rotated",
    "SelectedUVs",
    "Smooth",
    "TEXTURE_34_to_36",
    "TRANSFORM_Apply_Multi_User",
    "TRANSFORM_Distribute_X",
    "TRANSFORM_Distribute_Y",
    "TRANSFORM_Distribute_Z",
    "TRANSFORM_Mirror_3D_Cursor_YZ",
    "TRANSFORM_Mirror_Plane_Cursor",
    "TRANSFORM_Object_1m_Dimensions",
    "TRANSFORM_Object_Eigen_Matrix",
    "Trim_Name_After_Dot",
    "UEOPS_Clean_Old_Props",
    "UEOPS_Collection_From_Selection",
    "UEOPS_Copy_Attributes_to_Root",
    "UEOPS_Copy_Path_From_Selected",
    "UEOPS_QBlocker_Scale_Fix",
    "UEOPS_UCX_Name",
    "UV_Alpha_Toggle",
    "UV_BBOX_Fit",
    "UV_Closest_to_Cursor",
    "UV_Copy_From_Low",
    "UV_Cylinders_Cut",
    "UV_LongestEdge",
    "UV_LongestEdge_Complex",
    "UV_Mark_Cylinder_Seam",
    "UV_NaN_Cleaner",
    "UV_Offset_HIde",
    "UV_Pin_Toggle",
    "UV_Region_Clustering_Edit_Mode",
    "UV_Region_Clustering_Selected",
    "UV_Seam_Toggle",
    "UV_Select_Inverted",
    "UV_Select_Loop_Limited",
    "UV_Select_Non_Ch",
    "UV_Set_TD_Selected",
    "UV_Unwrap_Hide",
    "U_mat_text_prefix",
    "Unlink_Linked_Dot_Selected",
    "Wireframe_OFF",
    "XY_to_Zero",
    "Zero_Dimensions_Check",
    "_P4_Checkout_File",
    "_P4_Install",
    "_quick_rename",
    "export_assets_simple",
    "export_assets_to_fbx",
    "zzz_Clara_Transforms_Copy",
]


def search(query: str) -> list[tuple[str, int]]:
    """Run fuzzy_match against all scripts. Return matched (name, score) sorted by score."""
    results = []
    for name in ALL_SCRIPTS:
        matched, score = fuzzy_match(query, name)
        if matched:
            results.append((name, score))
    results.sort(key=lambda x: x[1])
    return results


def names(results: list[tuple[str, int]]) -> list[str]:
    """Extract just the names from search results."""
    return [r[0] for r in results]


# ---------------------------------------------------------------------------
# Test cases: (query, expected_must_contain, expected_must_not_contain, expected_first)
#   expected_must_contain:  scripts that MUST appear in results
#   expected_must_not_contain: scripts that must NOT appear
#   expected_first: if set, the top result(s) that should rank first
# ---------------------------------------------------------------------------
TEST_CASES = [
    # --- The reported bug case ---
    {
        "query": "name obj",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": ["NAME_Objects_from_Collections"],
        "description": "Reported bug: 'name obj' should find NAME_Objects_from_Collections",
    },
    # --- Single word, prefix match ---
    {
        "query": "clean",
        "must_contain": [
            "CLEAN_Console",
            "CLEAN_DataBlock",
            "CLEAN_Drivers_Remove",
            "CLEAN_Object_Color",
        ],
        "must_not_contain": ["NODE_Add", "UV_Pin_Toggle"],
        "first": [],
        "description": "Single word 'clean' matches all CLEAN_ prefixed scripts",
    },
    # --- Abbreviation ---
    {
        "query": "anim",
        "must_contain": [
            "ANIMATION_Rename_Actions",
            "ANIM_Clear_ApplyT_Reparent",
            "ANIM_Delete_Scale_Keyframes",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "'anim' should match ANIM_ and ANIMATION_ scripts",
    },
    # --- Two words, natural order ---
    {
        "query": "mod mirror",
        "must_contain": [
            "MOD_Mirror_Apply",
            "MOD_Mirror_Fix_Negative_Scale",
            "MOD_Mirror_Merge",
        ],
        "must_not_contain": ["NODE_Add", "UV_Pin_Toggle"],
        "first": [],
        "description": "Two words 'mod mirror' matches MOD_Mirror_* scripts",
    },
    # --- Two words, reversed order ---
    {
        "query": "mirror mod",
        "must_contain": [
            "MOD_Mirror_Apply",
            "MOD_Mirror_Fix_Negative_Scale",
            "MOD_Mirror_Merge",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "Reversed 'mirror mod' should still match (words in any order)",
    },
    # --- Short query ---
    {
        "query": "uv",
        "must_contain": [
            "UV_Alpha_Toggle",
            "UV_BBOX_Fit",
            "UV_Pin_Toggle",
            "UV_Seam_Toggle",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "Short query 'uv' matches UV_ scripts",
    },
    # --- Partial words ---
    {
        "query": "bool",
        "must_contain": [
            "BOOLEAN_Apply_Booleans",
            "BOOLEAN_Hide_Cutters",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "Partial word 'bool' matches BOOLEAN_ scripts",
    },
    # --- Multi-word partial ---
    {
        "query": "render cam",
        "must_contain": ["RENDER_Save_IMG_Current_Camera", "RENDER_ByCamera"],
        "must_not_contain": [],
        "first": [],
        "description": "'render cam' matches render scripts with camera",
    },
    # --- Numeric prefix ---
    {
        "query": "3d",
        "must_contain": ["3D_Cursor_Reset", "3D_Cursor_To_Custom"],
        "must_not_contain": [],
        "first": [],
        "description": "Numeric prefix '3d' matches 3D_ scripts",
    },
    # --- No match expected ---
    {
        "query": "xyzzyplugh",
        "must_contain": [],
        "must_not_contain": ALL_SCRIPTS,
        "first": [],
        "description": "Nonsense query matches nothing",
    },
    # --- Single character ---
    {
        "query": "s",
        "must_contain": ["Smooth", "SELECT_Polycount", "SORT_Collections_ABC"],
        "must_not_contain": [],
        "first": [],
        "description": "Single char 's' matches scripts starting with s",
    },
    # --- Underscore in query (should be treated as space) ---
    {
        "query": "name_obj",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": ["NAME_Objects_from_Collections"],
        "description": "Underscore in query treated as space",
    },
    # --- Case insensitive ---
    {
        "query": "NAME OBJ",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": ["NAME_Objects_from_Collections"],
        "description": "Uppercase query still matches",
    },
    # --- Multi-word, deeper match ---
    {
        "query": "select empty",
        "must_contain": [
            "CLEAN_Select_Empty_Materials",
            "SELECT_Toggle_Empty",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "'select empty' matches scripts with both words",
    },
    # --- Prefix of a category + specific word ---
    {
        "query": "col rename",
        "must_contain": [
            "COL_Rename_Selected",
            "COLLECTION_Rename_From_Empty",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "'col rename' matches COL_ and COLLECTION_ rename scripts",
    },
    # --- Very specific multi-word ---
    {
        "query": "vertex color remove",
        "must_contain": ["CLEAN_Vertex_Color_Remove"],
        "must_not_contain": [],
        "first": [],
        "description": "Three-word query narrows results",
    },
    # --- Partial mid-word ---
    {
        "query": "tex",
        "must_contain": ["TEXTURE_34_to_36", "FIX_Texture_Paths"],
        "must_not_contain": [],
        "first": [],
        "description": "'tex' matches TEXTURE and Texture",
    },
    # --- Empty query matches everything ---
    {
        "query": "",
        "must_contain": ALL_SCRIPTS[:5],
        "must_not_contain": [],
        "first": [],
        "description": "Empty query returns all scripts",
    },
    # --- Trailing space ---
    {
        "query": "name ",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap"],
        "must_not_contain": [],
        "first": [],
        "description": "Trailing space should still match (words split ignores empty)",
    },
    # --- Real user queries: typing progressively ---
    {
        "query": "n",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap", "NODE_Add"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'n'",
    },
    {
        "query": "na",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'na'",
    },
    {
        "query": "nam",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'nam'",
    },
    {
        "query": "name",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'name'",
    },
    {
        "query": "name ",
        "must_contain": ["NAME_Objects_from_Collections", "NAME_Swap"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'name ' (with space)",
    },
    {
        "query": "name o",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'name o'",
    },
    {
        "query": "name ob",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": [],
        "description": "Progressive typing: 'name ob'",
    },
    {
        "query": "name obj",
        "must_contain": ["NAME_Objects_from_Collections"],
        "must_not_contain": [],
        "first": ["NAME_Objects_from_Collections"],
        "description": "Progressive typing: 'name obj' (the reported bug)",
    },
    # --- Ranking: more specific match should rank higher ---
    {
        "query": "obj",
        "must_contain": [
            "OBJECT_Pack_Spheres",
            "NAME_Objects_from_Collections",
            "Objects_In_Grid",
        ],
        "must_not_contain": [],
        "first": [],
        "description": "'obj' matches OBJECT_ and other object-related scripts",
    },
]


def run_tests():
    passed = 0
    failed = 0
    errors = []

    for i, tc in enumerate(TEST_CASES):
        query = tc["query"]
        results = search(query)
        result_names = names(results)
        test_errors = []

        # Check must_contain
        for expected in tc["must_contain"]:
            if expected not in result_names:
                test_errors.append(f"  MISSING: '{expected}' not found in results")

        # Check must_not_contain
        for unexpected in tc["must_not_contain"]:
            if unexpected in result_names:
                test_errors.append(f"  UNEXPECTED: '{unexpected}' should not be in results")

        # Check first results
        for j, expected_first in enumerate(tc.get("first", [])):
            if j < len(result_names):
                if result_names[j] != expected_first:
                    test_errors.append(
                        f"  RANK: expected '{expected_first}' at position {j}, "
                        f"got '{result_names[j]}'"
                    )
            else:
                test_errors.append(
                    f"  RANK: expected '{expected_first}' at position {j}, "
                    f"but only {len(result_names)} results"
                )

        if test_errors:
            failed += 1
            errors.append((i, tc, result_names, test_errors))
        else:
            passed += 1

    # Print report
    print(f"\n{'='*70}")
    print(f"FUZZY SEARCH TEST RESULTS")
    print(f"{'='*70}")
    print(f"Passed: {passed}  Failed: {failed}  Total: {passed + failed}")
    print(f"{'='*70}\n")

    if errors:
        for i, tc, result_names, test_errors in errors:
            print(f"FAIL [{i}] query={tc['query']!r}")
            print(f"     {tc['description']}")
            print(f"     Got {len(result_names)} results: {result_names[:10]}{'...' if len(result_names) > 10 else ''}")
            for err in test_errors:
                print(err)
            print()

    # Also print a summary table of all queries and their match counts
    print(f"\n{'='*70}")
    print(f"QUERY SUMMARY (all test cases)")
    print(f"{'='*70}")
    print(f"{'Query':<25} {'Matches':>7}  {'Top 3 results'}")
    print(f"{'-'*25} {'-'*7}  {'-'*37}")
    for tc in TEST_CASES:
        q = tc["query"]
        r = search(q)
        top3 = ", ".join(names(r)[:3])
        print(f"{q!r:<25} {len(r):>7}  {top3}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
