########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from bpy.props import *
from bpy.types import PropertyGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from . import GET_TYPE_SET, STATUS_OPTS, SPACE_OPTS, SURFACE_OPTS, TOOL_OPTS, SHAPE_OPTS


class PS_PROPS_Razor_Ops(PropertyGroup):
    active   : BoolProperty(name="Active" , default=False)
    in_menu : BoolProperty(name="In Menu", default=False)
    status  : EnumProperty(name="Status" , items=STATUS_OPTS , default='FINISHED')
    space   : EnumProperty(name="Space"  , items=SPACE_OPTS  , default='VIEW_3D')
    surface : EnumProperty(name="Surface", items=SURFACE_OPTS, default='NONE')
    tool    : EnumProperty(name="Tool"   , items=TOOL_OPTS   , default='SKETCH')
    shape   : EnumProperty(name="Shape"  , items=SHAPE_OPTS  , default='RECTANGLE')

    def reset(self):
        self.active = False
        self.status = 'FINISHED'
        self.surface = 'NONE'
        self.tool = 'SKETCH'
        self.shape = 'RECTANGLE'
