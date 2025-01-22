########################•########################
"""                   KodoPy                  """
########################•########################

import bpy
from bpy.types import PropertyGroup
from bpy.props import BoolProperty, FloatProperty, EnumProperty, IntProperty, FloatVectorProperty


class PS_PROPS_HUD_Gizmo(PropertyGroup):
    show_gizmos      : BoolProperty(name="Show Edit Mesh Gizmos", default=True)
    screen_padding   : IntProperty(name="Screen Padding", min=0, default=70)
    align_horizontal : BoolProperty(name="Align Horizontal", default=True)
    offset_x : IntProperty(name="Offset X", default=0)
    offset_y : IntProperty(name="Offset Y", default=4000)

    razor_color  : FloatVectorProperty(name="Razor HUD Color" , size=3, min=0, max=1, subtype='COLOR', default=(8/32, 3/32, 0))
    select_color : FloatVectorProperty(name="Select HUD Color", size=3, min=0, max=1, subtype='COLOR', default=(0, 6/32, 6/32))
    edit_color   : FloatVectorProperty(name="Edit HUD Color"  , size=3, min=0, max=1, subtype='COLOR', default=(0, 0, 6/32))
    marks_color  : FloatVectorProperty(name="Marks HUD Color" , size=3, min=0, max=1, subtype='COLOR', default=(0, 0, 0))