########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from bpy.props import *
from bpy.types import PropertyGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from . import PROPS_BASE, PROPS_UUID, ENTITY_EDIT_OPTS


class PS_PROPS_Razor_Edit_Features(PROPS_BASE, PROPS_UUID):
    operation    : EnumProperty(name="Operation", items=ENTITY_EDIT_OPTS, default='NONE')
    entity_A_uid : StringProperty(name="Entity A UID", default="")
    entity_B_uid : StringProperty(name="Entity B UID", default="")


class PS_PROPS_Razor_Part_Features(PROPS_BASE, PROPS_UUID):
    use_extrude : BoolProperty(name="Use Extrude", default=True)
    use_mirror  : BoolProperty(name="Use Mirror", default=True)
    use_array   : BoolProperty(name="Use Array", default=False)
