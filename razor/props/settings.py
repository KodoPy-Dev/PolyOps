########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
import math
from bpy.props import *
from bpy.types import PropertyGroup
from mathutils import geometry, Vector, Matrix, Euler, Quaternion
from . import BOOLEAN_SOLVER_OPTS

########################•########################
"""                   PROPS                   """
########################•########################

class PS_PROPS_Razor_Settings(PropertyGroup):
    is_destructive_mode : BoolProperty(name="Destructive Mode", default=False)
    boolean_solver_mode : EnumProperty(name="Boolean Solver", items=BOOLEAN_SOLVER_OPTS, default='FAST')

    # --- WORKPLANE --- #

    max_workplanes            : IntProperty(name="Max Workplanes", default=16, min=1, max=64)
    grid_active_color         : FloatVectorProperty(name="grid_active_color"       , default=(1.0, 1.0, 1.0, 1/16), size=4, min=0, max=1, subtype='COLOR')
    grid_inactive_color       : FloatVectorProperty(name="grid_inactive_color"     , default=(1.0, 1.0, 1.0, 1/64), size=4, min=0, max=1, subtype='COLOR')
    workplane_modal_color     : FloatVectorProperty(name="workplane_modal_color"   , default=(0.2, 1.0, 0.0, 1.0), size=4, min=0, max=1, subtype='COLOR')
    workplane_select_color    : FloatVectorProperty(name="workplane_select_color"  , default=(1.0, 1.0, 0.0, 1.0), size=4, min=0, max=1, subtype='COLOR')
    workplane_active_color    : FloatVectorProperty(name="workplane_active_color"  , default=(1.0, 0.3, 0.0, 1.0), size=4, min=0, max=1, subtype='COLOR')
    workplane_inactive_color  : FloatVectorProperty(name="workplane_inactive_color", default=(1.0, 0.3, 0.0, 0.3), size=4, min=0, max=1, subtype='COLOR')
