########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty, FloatVectorProperty


class PS_PROPS_Object(PropertyGroup):
    use_for_boolean: BoolProperty(name="Used For Boolean", default=False)
    


