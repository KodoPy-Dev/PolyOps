########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty, FloatVectorProperty


class PS_PROPS_Mesh(PropertyGroup):
    is_backup: BoolProperty(name="Is Mesh Backup", default=False)


