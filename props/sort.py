########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, StringProperty, IntProperty


class PS_PROPS_Sort(PropertyGroup):
    # --- SORT : GLOBAL --- #
    sort_enabled : BoolProperty(name="sort_enabled", default=True, description="Enable / Disable Sorting for all Objects")
    ignore_sort_str: StringProperty(name="ignore_sort_str", default="<R7>")

    # --- SORT : TOP --- #
    top_mirror : BoolProperty(name="top_mirror", default=True)
    top_mirror_count : IntProperty(name="top_mirrors_count", min=1, default=1, description="How many Mirror Modifiers to sort")
    top_mirror_check_no_bisect : BoolProperty(name="top_mirror_check_no_bisect", default=True, description="On → Mirror must NOT be using bisect\nOff → Mirror can use bisect")
    top_mirror_check_no_object : BoolProperty(name="top_mirror_check_no_object", default=True, description="On → Mirror must NOT be using an Object\nOff → Mirror can use an Object")

    top_bevel : BoolProperty(name="top_bevel", default=True)
    top_bevel_count : IntProperty(name="top_bevels_count", min=1, default=1, description="How many Bevel Modifiers to sort")
    top_bevel_require_vgroup : BoolProperty(name="top_bevels_require_vgroup", default=True, description="On → Modifier must use a V-Group\nOff → Ignores V-Group when sorting")

    top_solidify : BoolProperty(name="top_solidify", default=True)
    top_solidify_count : IntProperty(name="top_solidify_count", min=1, default=1, description="How many Solidify Modifiers to sort")
    top_solidify_require_vgroup : BoolProperty(name="top_solidify_require_vgroup", default=True, description="On → Modifier must use a V-Group\nOff → Ignores V-Group when sorting")

    top_deform : BoolProperty(name="top_deform", default=True)
    top_deform_count : IntProperty(name="top_deform_count", min=1, default=1, description="How many Simple Deform Modifiers to sort")
    top_deform_require_vgroup : BoolProperty(name="top_deform_require_vgroup", default=True, description="On → Modifier must use a V-Group\nOff → Ignores V-Group when sorting")

    top_edge_split : BoolProperty(name="top_edge_split", default=True)
    top_edge_split_count : IntProperty(name="top_edge_split_count", min=1, default=1, description="How many Edge-Split Modifiers to sort")
    top_edge_split_require_sharp : BoolProperty(name="top_edge_split_require_sharp", default=True, description="On → Modifier must use Edge Sharp\nOff → Ignores Edge Sharp when sorting")

    top_subsurf : BoolProperty(name="top_subsurf", default=True)
    top_subsurf_count : IntProperty(name="top_subsurf_count", min=1, default=1, description="How many Sub-Surf Modifiers to sort")

    # --- SORT : BOOLEANS --- #
    boolean_to_bevel : BoolProperty(name="boolean_to_bevel", default=True)
    boolean_to_solidify : BoolProperty(name="boolean_to_solidify", default=True)
    boolean_to_subsurf : BoolProperty(name="boolean_to_subsurf", default=True)
    boolean_to_mirror : BoolProperty(name="boolean_to_mirror", default=True)
    boolean_to_array : BoolProperty(name="boolean_to_array", default=False)

    # --- SORT : BOTTOM --- #
    bottom_mirror : BoolProperty(name="bottom_mirror", default=True)
    bottom_weld : BoolProperty(name="bottom_weld", default=True)
    bottom_autosmooth : BoolProperty(name="bottom_autosmooth", default=True)
    bottom_weighted_normal : BoolProperty(name="bottom_weighted_normal", default=True)
    bottom_array : BoolProperty(name="bottom_array", default=True)
    bottom_deform : BoolProperty(name="bottom_deform", default=True)
    bottom_triangulate : BoolProperty(name="bottom_triangulate", default=True)

